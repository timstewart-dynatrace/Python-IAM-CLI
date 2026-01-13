"""OAuth2 authentication utilities for Dynatrace Account Management API.

Handles OAuth2 token acquisition, caching, and refresh for the IAM API.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def extract_client_id_from_secret(client_secret: str) -> str | None:
    """Extract the client ID from a Dynatrace OAuth client secret.

    Dynatrace OAuth client secrets follow the format:
        dt0s01.XXXXXXXX.YYYYYYYYYYYYYYYY

    Where the client_id is the first two dot-separated segments:
        dt0s01.XXXXXXXX

    Args:
        client_secret: The full OAuth client secret

    Returns:
        The extracted client ID, or None if the secret format is invalid
    """
    if not client_secret:
        return None

    parts = client_secret.split(".")
    if len(parts) < 3:
        logger.warning(
            "Client secret does not match expected format (dt0s01.XXXXXXXX.YYYY...). "
            "Cannot auto-extract client ID."
        )
        return None

    # Client ID is the first two parts: dt0s01.XXXXXXXX
    client_id = f"{parts[0]}.{parts[1]}"
    logger.debug(f"Auto-extracted client ID: {client_id}")
    return client_id


# OAuth2 scopes required for IAM and platform operations
IAM_SCOPES = (
    "account-idm-read iam:users:read iam:groups:read account-idm-write "
    "account-env-read account-env-write account-uac-read account-uac-write "
    "iam-policies-management iam:policies:write "
    "iam:policies:read iam:bindings:write iam:bindings:read "
    "iam:effective-permissions:read "
    "iam:boundaries:read iam:boundaries:write "
    "app-engine:apps:run"  # Required for App Engine Registry API (get apps)
)

TOKEN_URL = "https://sso.dynatrace.com/sso/oauth2/token"


@dataclass
class TokenInfo:
    """Cached OAuth2 token information."""

    access_token: str
    expires_at: float
    scope: str


class OAuthError(Exception):
    """Exception raised for OAuth2 authentication errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        error_description: str | None = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.error_description = error_description


class BaseTokenManager:
    """Base class for token managers."""

    def get_token(self, force_refresh: bool = False) -> str:
        """Get a valid access token."""
        raise NotImplementedError

    def get_headers(self, force_refresh: bool = False) -> dict[str, str]:
        """Get HTTP headers with valid Authorization token."""
        raise NotImplementedError

    def is_token_valid(self) -> bool:
        """Check if the token is still valid."""
        raise NotImplementedError

    def close(self) -> None:
        """Clean up resources."""
        pass


class StaticTokenManager(BaseTokenManager):
    """Token manager that uses a pre-existing bearer token.

    WARNING: Static tokens do not auto-refresh. When the token expires,
    requests will fail with 401 Unauthorized. This is suitable for:
    - Short-lived interactive sessions
    - Testing and debugging
    - Integration with systems that provide tokens externally

    For long-running automation, use TokenManager with OAuth2 credentials instead.
    """

    def __init__(self, token: str):
        """Initialize with a static bearer token.

        Args:
            token: Bearer token string (without "Bearer " prefix)
        """
        self._token = token
        logger.warning(
            "Using static bearer token. Token will NOT auto-refresh. "
            "Requests will fail when token expires."
        )

    def get_token(self, force_refresh: bool = False) -> str:
        """Get the static token.

        Args:
            force_refresh: Ignored for static tokens (cannot refresh)

        Returns:
            The static token string
        """
        if force_refresh:
            logger.warning("Cannot refresh static bearer token. Use OAuth2 for auto-refresh.")
        return self._token

    def get_headers(self, force_refresh: bool = False) -> dict[str, str]:
        """Get HTTP headers with the static token.

        Args:
            force_refresh: Ignored for static tokens

        Returns:
            Headers dict with Authorization Bearer token
        """
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

    def is_token_valid(self) -> bool:
        """Check if token exists (cannot verify expiration for static tokens)."""
        return bool(self._token)

    def clear_cache(self) -> None:
        """No-op for static tokens."""
        pass


class TokenManager(BaseTokenManager):
    """Manages OAuth2 token acquisition and caching.

    This is the recommended authentication method for automation and long-running
    processes. Tokens are automatically refreshed when they expire.

    Requires OAuth2 client credentials (client_id and client_secret) which can be
    created in Dynatrace Account Management -> OAuth clients.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        account_uuid: str,
        scope: str = IAM_SCOPES,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.account_uuid = account_uuid
        self.scope = scope
        self._token: TokenInfo | None = None
        self._http_client: httpx.Client | None = None

    @property
    def http_client(self) -> httpx.Client:
        """Lazily create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=30.0)
        return self._http_client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def __enter__(self) -> "TokenManager":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def is_token_valid(self) -> bool:
        """Check if the cached token is still valid (with 30s buffer)."""
        if self._token is None:
            return False
        return time.time() < (self._token.expires_at - 30)

    def get_token(self, force_refresh: bool = False) -> str:
        """Get a valid access token, refreshing if necessary.

        Args:
            force_refresh: Force token refresh even if cached token is valid.

        Returns:
            Valid access token string.

        Raises:
            OAuthError: If token acquisition fails.
        """
        if not force_refresh and self.is_token_valid():
            logger.debug("Using cached OAuth token")
            return self._token.access_token  # type: ignore[union-attr]

        self._refresh_token()
        return self._token.access_token  # type: ignore[union-attr]

    def _refresh_token(self) -> None:
        """Fetch a new access token from the OAuth2 server."""
        logger.info("Requesting OAuth2 access token from Dynatrace SSO...")

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
            "resource": f"urn:dtaccount:{self.account_uuid}",
        }

        logger.debug(f"Token endpoint: {TOKEN_URL}")
        logger.debug(f"Resource: urn:dtaccount:{self.account_uuid}")

        try:
            response = self.http_client.post(
                TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if not response.is_success:
                self._handle_error_response(response)

            token_data = response.json()
            access_token = token_data.get("access_token")
            expires_in = int(token_data.get("expires_in", 300))

            if not access_token:
                raise OAuthError("No access_token in response")

            self._token = TokenInfo(
                access_token=access_token,
                expires_at=time.time() + expires_in,
                scope=token_data.get("scope", self.scope),
            )

            logger.info(f"OAuth2 token retrieved successfully (expires in {expires_in}s)")

        except httpx.RequestError as e:
            raise OAuthError(f"Connection error: {e}") from e

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle OAuth2 error response."""
        error_code = None
        error_description = None

        try:
            error_data = response.json()
            error_code = error_data.get("error")
            error_description = error_data.get("error_description")
        except Exception:
            pass

        logger.error(f"OAuth2 token request failed: HTTP {response.status_code}")
        if error_code:
            logger.error(f"Error code: {error_code}")
        if error_description:
            logger.error(f"Error description: {error_description}")

        raise OAuthError(
            f"Token request failed: {response.status_code}",
            error_code=error_code,
            error_description=error_description,
        )

    def get_headers(self, force_refresh: bool = False) -> dict[str, str]:
        """Get HTTP headers with valid Authorization token.

        Args:
            force_refresh: Force token refresh even if cached token is valid.

        Returns:
            Headers dict with Authorization Bearer token.
        """
        token = self.get_token(force_refresh=force_refresh)
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    def clear_cache(self) -> None:
        """Clear the cached token."""
        self._token = None
        logger.debug("Token cache cleared")
