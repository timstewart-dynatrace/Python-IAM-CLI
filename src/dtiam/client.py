"""HTTP client for Dynatrace IAM API interactions.

Provides a robust HTTP client with:
- OAuth2 authentication with automatic token refresh
- Automatic retry with exponential backoff
- Rate limit handling (429)
- Configurable timeout
- Debug/verbose logging
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx
from pydantic import BaseModel

from dtiam.config import Config, load_config, get_env_override
from dtiam.utils.auth import (
    TokenManager,
    StaticTokenManager,
    BaseTokenManager,
    OAuthError,
    extract_client_id_from_secret,
)

logger = logging.getLogger(__name__)

# Dynatrace IAM API base URL
IAM_API_BASE = "https://api.dynatrace.com/iam/v1"


class APIError(Exception):
    """Exception raised for API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""

    max_retries: int = 3
    retry_statuses: list[int] = [429, 500, 502, 503, 504]
    initial_delay: float = 1.0
    max_delay: float = 10.0
    exponential_base: float = 2.0


class Client:
    """HTTP client for Dynatrace IAM API with OAuth2 or bearer token auth and retry handling.

    Also supports optional environment-level API token for management zones (legacy feature).
    """

    def __init__(
        self,
        account_uuid: str,
        token_manager: BaseTokenManager,
        timeout: float = 30.0,
        retry_config: RetryConfig | None = None,
        verbose: bool = False,
        environment_token: str | None = None,
    ):
        self.account_uuid = account_uuid
        self.token_manager = token_manager
        self.timeout = timeout
        self.retry_config = retry_config or RetryConfig()
        self.verbose = verbose
        self.environment_token = environment_token  # Optional environment API token

        self.base_url = f"{IAM_API_BASE}/accounts/{account_uuid}"

        self._client = httpx.Client(
            timeout=timeout,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "dtiam/3.7.0",
            },
        )

    def close(self) -> None:
        """Close the HTTP client and token manager."""
        self._client.close()
        self.token_manager.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _get_auth_headers(self, use_environment_token: bool = False) -> dict[str, str]:
        """Get current authentication headers.

        Args:
            use_environment_token: If True and environment_token is set, use that instead

        Returns:
            Dictionary with authorization headers
        """
        if use_environment_token and self.environment_token:
            return {"Authorization": f"Api-Token {self.environment_token}"}
        return self.token_manager.get_headers()

    def _should_retry(self, status_code: int) -> bool:
        """Check if request should be retried based on status code."""
        return status_code in self.retry_config.retry_statuses

    def _get_retry_delay(self, attempt: int, response: httpx.Response | None = None) -> float:
        """Calculate delay before next retry attempt."""
        # Check for Retry-After header (rate limiting)
        if response is not None and "Retry-After" in response.headers:
            try:
                return float(response.headers["Retry-After"])
            except ValueError:
                pass

        # Exponential backoff
        delay = self.retry_config.initial_delay * (
            self.retry_config.exponential_base ** attempt
        )
        return min(delay, self.retry_config.max_delay)

    def _log_request(self, method: str, url: str, **kwargs: Any) -> None:
        """Log request details in verbose mode."""
        if self.verbose:
            logger.debug(f"Request: {method} {url}")
            if "headers" in kwargs:
                headers = kwargs["headers"]
                auth_header = headers.get("Authorization", "None")
                logger.debug(f"Auth: {auth_header[:20]}..." if len(auth_header) > 20 else f"Auth: {auth_header}")
            if "json" in kwargs:
                logger.debug(f"Body: {kwargs['json']}")

    def _log_response(self, response: httpx.Response) -> None:
        """Log response details in verbose mode."""
        if self.verbose:
            logger.debug(f"Response: {response.status_code}")
            if response.text:
                logger.debug(f"Body: {response.text[:500]}...")

    def request(
        self,
        method: str,
        path: str,
        use_environment_token: bool = False,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: API path (will be joined with base_url if relative)
            use_environment_token: Use environment token for environment API calls (default: False)
            **kwargs: Additional arguments passed to httpx

        Returns:
            httpx.Response object

        Raises:
            APIError: If request fails after all retries
        """
        # Build full URL
        if path.startswith("http"):
            url = path
            # Auto-detect environment API calls (for management zones)
            # Note: .apps.dynatrace.com (App Engine Registry) uses OAuth2 Bearer tokens,
            # NOT environment API tokens, so we don't include it here
            if ".live.dynatrace.com" in url:
                use_environment_token = True
        elif path.startswith("/"):
            url = f"{self.base_url}{path}"
        else:
            url = f"{self.base_url}/{path}"

        last_exception: Exception | None = None
        last_response: httpx.Response | None = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                # Get fresh auth headers for each attempt
                headers = {**self._get_auth_headers(use_environment_token), **kwargs.pop("headers", {})}
                
                # Log request with headers
                if self.verbose:
                    logger.debug(f"Request: {method} {url}")
                    auth_header = headers.get("Authorization", "None")
                    logger.debug(f"Auth: {auth_header[:30]}..." if len(auth_header) > 30 else f"Auth: {auth_header}")

                response = self._client.request(method, url, headers=headers, **kwargs)
                self._log_response(response)

                if response.is_success:
                    return response

                if not self._should_retry(response.status_code):
                    raise APIError(
                        f"Request failed: {response.status_code} {response.reason_phrase}",
                        status_code=response.status_code,
                        response_body=response.text,
                    )

                last_response = response

            except httpx.RequestError as e:
                last_exception = e
                if attempt == self.retry_config.max_retries:
                    raise APIError(f"Request failed: {e}") from e

            # Calculate retry delay
            if attempt < self.retry_config.max_retries:
                delay = self._get_retry_delay(attempt, last_response)
                if self.verbose:
                    logger.debug(f"Retrying in {delay:.1f}s (attempt {attempt + 1})")
                time.sleep(delay)

        # All retries exhausted
        if last_response is not None:
            raise APIError(
                f"Request failed after {self.retry_config.max_retries} retries: "
                f"{last_response.status_code}",
                status_code=last_response.status_code,
                response_body=last_response.text,
            )

        raise APIError(
            f"Request failed after {self.retry_config.max_retries} retries: {last_exception}"
        )

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make a GET request."""
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make a POST request."""
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make a PUT request."""
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make a PATCH request."""
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make a DELETE request."""
        return self.request("DELETE", path, **kwargs)


def create_client_from_config(
    config: Config | None = None,
    context_name: str | None = None,
    verbose: bool = False,
) -> Client:
    """Create a client from configuration.

    Authentication Priority (first match wins):
    1. DTIAM_BEARER_TOKEN + DTIAM_ACCOUNT_UUID (static bearer token)
    2. DTIAM_CLIENT_SECRET + DTIAM_ACCOUNT_UUID (OAuth2 via env, client ID auto-extracted)
    3. Config file context with OAuth2 credentials

    Note: DTIAM_CLIENT_ID is optional - if not set, it will be automatically
    extracted from DTIAM_CLIENT_SECRET (format: dt0s01.CLIENTID.SECRETPART).

    Optional Environment Token for Management Zones (legacy):
    - DTIAM_ENVIRONMENT_TOKEN: Environment API token for management zone operations

    Args:
        config: Configuration object (loads from file if not provided)
        context_name: Override context name (uses current-context if not provided)
        verbose: Enable verbose logging

    Returns:
        Configured Client instance

    Raises:
        RuntimeError: If no context or credentials are configured
    """
    if config is None:
        config = load_config()

    # Check for environment variable overrides
    ctx_name = get_env_override("context") or context_name or config.current_context

    # Check for optional environment token (for management zones)
    env_token = os.environ.get("DTIAM_ENVIRONMENT_TOKEN")

    # Priority 1: Bearer token (static, no auto-refresh)
    env_bearer_token = get_env_override("bearer_token")
    env_account_uuid = get_env_override("account_uuid")

    if env_bearer_token and env_account_uuid:
        logger.info("Using bearer token authentication (no auto-refresh)")
        token_manager: BaseTokenManager = StaticTokenManager(token=env_bearer_token)
        return Client(
            account_uuid=env_account_uuid,
            token_manager=token_manager,
            verbose=verbose,
            environment_token=env_token,
        )

    # Priority 2: OAuth2 via environment variables (auto-refresh)
    env_client_id = get_env_override("client_id")
    env_client_secret = get_env_override("client_secret")

    # Auto-extract client ID from secret if not provided
    if env_client_secret and not env_client_id:
        env_client_id = extract_client_id_from_secret(env_client_secret)
        if env_client_id:
            logger.info(f"Auto-extracted client ID from DTIAM_CLIENT_SECRET")

    if env_client_id and env_client_secret and env_account_uuid:
        logger.info("Using OAuth2 authentication via environment variables")
        token_manager = TokenManager(
            client_id=env_client_id,
            client_secret=env_client_secret,
            account_uuid=env_account_uuid,
        )
        return Client(
            account_uuid=env_account_uuid,
            token_manager=token_manager,
            verbose=verbose,
            environment_token=env_token,
        )

    # Priority 3: Config file with OAuth2 credentials
    if not ctx_name:
        raise RuntimeError(
            "No authentication configured. Options:\n"
            "  1. Bearer token: Set DTIAM_BEARER_TOKEN and DTIAM_ACCOUNT_UUID\n"
            "  2. OAuth2 env: Set DTIAM_CLIENT_ID, DTIAM_CLIENT_SECRET, DTIAM_ACCOUNT_UUID\n"
            "  3. Config file: Run 'dtiam config set-context' and 'dtiam config set-credentials'"
        )

    context = config.get_context(ctx_name)
    if not context:
        raise RuntimeError(f"Context '{ctx_name}' not found in configuration.")

    credential = config.get_credential(context.credentials_ref)
    if not credential:
        raise RuntimeError(
            f"Credential '{context.credentials_ref}' not found. "
            "Use 'dtiam config set-credentials' to add it."
        )

    logger.info(f"Using OAuth2 authentication via config context '{ctx_name}'")
    token_manager = TokenManager(
        client_id=credential.client_id,
        client_secret=credential.client_secret,
        account_uuid=context.account_uuid,
    )

    # Use environment token from credential if no env override, or use credential's env token if available
    final_env_token = env_token or credential.environment_token

    return Client(
        account_uuid=context.account_uuid,
        token_manager=token_manager,
        verbose=verbose,
        environment_token=final_env_token,
    )
