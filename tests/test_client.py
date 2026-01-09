"""Tests for the HTTP client module."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from dtiam.client import (
    Client,
    APIError,
    RetryConfig,
    IAM_API_BASE,
    create_client_from_config,
)
from dtiam.config import Config, Context, Credential, NamedContext, NamedCredential


class TestAPIError:
    """Tests for APIError exception."""

    def test_api_error_basic(self):
        """Test basic APIError."""
        error = APIError("Test error")
        assert str(error) == "Test error"
        assert error.status_code is None
        assert error.response_body is None

    def test_api_error_with_details(self):
        """Test APIError with status code and body."""
        error = APIError(
            "Test error",
            status_code=404,
            response_body='{"error": "Not found"}',
        )
        assert error.status_code == 404
        assert error.response_body == '{"error": "Not found"}'


class TestRetryConfig:
    """Tests for RetryConfig class."""

    def test_default_retry_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert 429 in config.retry_statuses
        assert 500 in config.retry_statuses
        assert config.initial_delay == 1.0
        assert config.max_delay == 10.0
        assert config.exponential_base == 2.0

    def test_custom_retry_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_retries=5,
            retry_statuses=[500, 503],
            initial_delay=0.5,
            max_delay=30.0,
        )
        assert config.max_retries == 5
        assert config.retry_statuses == [500, 503]
        assert config.initial_delay == 0.5
        assert config.max_delay == 30.0


class TestClient:
    """Tests for Client class."""

    @pytest.fixture
    def mock_token_manager(self):
        """Create a mock token manager."""
        manager = MagicMock()
        manager.get_headers.return_value = {"Authorization": "Bearer test-token"}
        return manager

    @pytest.fixture
    def client(self, mock_token_manager):
        """Create a client for testing."""
        return Client(
            account_uuid="test-account",
            token_manager=mock_token_manager,
            timeout=30.0,
            verbose=False,
        )

    def test_client_initialization(self, mock_token_manager):
        """Test client initialization."""
        client = Client(
            account_uuid="my-account",
            token_manager=mock_token_manager,
            timeout=60.0,
            verbose=True,
        )
        assert client.account_uuid == "my-account"
        assert client.timeout == 60.0
        assert client.verbose is True
        assert f"{IAM_API_BASE}/accounts/my-account" == client.base_url

    def test_client_base_url(self, client):
        """Test client base URL construction."""
        expected = f"{IAM_API_BASE}/accounts/test-account"
        assert client.base_url == expected

    def test_client_context_manager(self, mock_token_manager):
        """Test client can be used as context manager."""
        with Client(
            account_uuid="test",
            token_manager=mock_token_manager,
        ) as client:
            assert client is not None

    def test_should_retry_retryable_status(self, client):
        """Test _should_retry with retryable status codes."""
        assert client._should_retry(429) is True
        assert client._should_retry(500) is True
        assert client._should_retry(502) is True
        assert client._should_retry(503) is True
        assert client._should_retry(504) is True

    def test_should_retry_non_retryable_status(self, client):
        """Test _should_retry with non-retryable status codes."""
        assert client._should_retry(200) is False
        assert client._should_retry(400) is False
        assert client._should_retry(401) is False
        assert client._should_retry(403) is False
        assert client._should_retry(404) is False

    def test_get_retry_delay_exponential(self, client):
        """Test exponential backoff delay calculation."""
        delay0 = client._get_retry_delay(0)
        delay1 = client._get_retry_delay(1)
        delay2 = client._get_retry_delay(2)

        assert delay0 == 1.0  # initial_delay * 2^0
        assert delay1 == 2.0  # initial_delay * 2^1
        assert delay2 == 4.0  # initial_delay * 2^2

    def test_get_retry_delay_max_cap(self, client):
        """Test retry delay is capped at max_delay."""
        # High attempt number should cap at max_delay
        delay = client._get_retry_delay(10)
        assert delay == client.retry_config.max_delay

    def test_get_retry_delay_from_header(self, client):
        """Test retry delay from Retry-After header."""
        mock_response = MagicMock()
        mock_response.headers = {"Retry-After": "5"}

        delay = client._get_retry_delay(0, mock_response)
        assert delay == 5.0

    def test_get_auth_headers(self, client):
        """Test getting authentication headers."""
        headers = client._get_auth_headers()
        assert headers == {"Authorization": "Bearer test-token"}

    def test_request_success(self, client):
        """Test successful request."""
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200

        with patch.object(client._client, "request") as mock_request:
            mock_request.return_value = mock_response

            response = client.get("/groups")

            assert response == mock_response

    def test_request_with_absolute_url(self, client):
        """Test request with absolute URL."""
        mock_response = MagicMock()
        mock_response.is_success = True

        with patch.object(client._client, "request") as mock_request:
            mock_request.return_value = mock_response

            client.request("GET", "https://example.com/api/test")

            call_args = mock_request.call_args
            assert call_args[0][1] == "https://example.com/api/test"

    def test_request_with_relative_path(self, client):
        """Test request with relative path."""
        mock_response = MagicMock()
        mock_response.is_success = True

        with patch.object(client._client, "request") as mock_request:
            mock_request.return_value = mock_response

            client.request("GET", "groups")

            call_args = mock_request.call_args
            assert call_args[0][1] == f"{client.base_url}/groups"

    def test_request_non_retryable_error(self, client):
        """Test request fails on non-retryable error."""
        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 404
        mock_response.reason_phrase = "Not Found"
        mock_response.text = "Resource not found"

        with patch.object(client._client, "request") as mock_request:
            mock_request.return_value = mock_response

            with pytest.raises(APIError) as exc_info:
                client.get("/groups/nonexistent")

            assert exc_info.value.status_code == 404

    def test_http_method_shortcuts(self, client):
        """Test HTTP method shortcut methods."""
        mock_response = MagicMock()
        mock_response.is_success = True

        with patch.object(client, "request") as mock_request:
            mock_request.return_value = mock_response

            client.get("/path")
            mock_request.assert_called_with("GET", "/path")

            client.post("/path", json={"data": "test"})
            mock_request.assert_called_with("POST", "/path", json={"data": "test"})

            client.put("/path", json={"data": "test"})
            mock_request.assert_called_with("PUT", "/path", json={"data": "test"})

            client.patch("/path", json={"data": "test"})
            mock_request.assert_called_with("PATCH", "/path", json={"data": "test"})

            client.delete("/path")
            mock_request.assert_called_with("DELETE", "/path")


class TestCreateClientFromConfig:
    """Tests for create_client_from_config function."""

    def test_create_client_from_env_vars(self):
        """Test creating client from environment variables."""
        with patch("dtiam.client.get_env_override") as mock_env:
            mock_env.side_effect = lambda key: {
                "client_id": "env-client-id",
                "client_secret": "env-secret",
                "account_uuid": "env-account",
                "context": None,
            }.get(key)

            with patch("dtiam.client.TokenManager") as mock_tm:
                mock_tm.return_value = MagicMock()

                client = create_client_from_config()

                assert client.account_uuid == "env-account"
                mock_tm.assert_called_once_with(
                    client_id="env-client-id",
                    client_secret="env-secret",
                    account_uuid="env-account",
                )

    def test_create_client_from_config_file(self):
        """Test creating client from config file."""
        config = Config()
        config.current_context = "test"
        config.contexts = [
            NamedContext(
                name="test",
                context=Context(
                    account_uuid="config-account",
                    credentials_ref="test-creds",
                ),
            )
        ]
        config.credentials = [
            NamedCredential(
                name="test-creds",
                credential=Credential(
                    client_id="config-client-id",
                    client_secret="config-secret",
                ),
            )
        ]

        with patch("dtiam.client.get_env_override") as mock_env:
            mock_env.return_value = None

            with patch("dtiam.client.TokenManager") as mock_tm:
                mock_tm.return_value = MagicMock()

                client = create_client_from_config(config=config)

                assert client.account_uuid == "config-account"

    def test_create_client_no_context(self):
        """Test error when no context is configured."""
        config = Config()  # Empty config

        with patch("dtiam.client.get_env_override") as mock_env:
            mock_env.return_value = None

            with pytest.raises(RuntimeError, match="No authentication configured"):
                create_client_from_config(config=config)

    def test_create_client_context_not_found(self):
        """Test error when specified context is not found."""
        config = Config()
        config.current_context = "nonexistent"

        with patch("dtiam.client.get_env_override") as mock_env:
            mock_env.return_value = None

            with pytest.raises(RuntimeError, match="not found"):
                create_client_from_config(config=config)

    def test_create_client_credentials_not_found(self):
        """Test error when credentials are not found."""
        config = Config()
        config.current_context = "test"
        config.contexts = [
            NamedContext(
                name="test",
                context=Context(
                    account_uuid="test-account",
                    credentials_ref="missing-creds",
                ),
            )
        ]

        with patch("dtiam.client.get_env_override") as mock_env:
            mock_env.return_value = None

            with pytest.raises(RuntimeError, match="Credential.*not found"):
                create_client_from_config(config=config)

    def test_create_client_with_context_override(self):
        """Test creating client with context name override."""
        config = Config()
        config.current_context = "default"
        config.contexts = [
            NamedContext(
                name="default",
                context=Context(
                    account_uuid="default-account",
                    credentials_ref="default-creds",
                ),
            ),
            NamedContext(
                name="override",
                context=Context(
                    account_uuid="override-account",
                    credentials_ref="override-creds",
                ),
            ),
        ]
        config.credentials = [
            NamedCredential(
                name="default-creds",
                credential=Credential(
                    client_id="default-id",
                    client_secret="default-secret",
                ),
            ),
            NamedCredential(
                name="override-creds",
                credential=Credential(
                    client_id="override-id",
                    client_secret="override-secret",
                ),
            ),
        ]

        with patch("dtiam.client.get_env_override") as mock_env:
            mock_env.return_value = None

            with patch("dtiam.client.TokenManager") as mock_tm:
                mock_tm.return_value = MagicMock()

                client = create_client_from_config(
                    config=config,
                    context_name="override",
                )

                assert client.account_uuid == "override-account"

