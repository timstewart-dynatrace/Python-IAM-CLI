"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from dtiam.client import Client
from dtiam.config import Config, Context, Credential, NamedContext, NamedCredential


# Sample data for tests
SAMPLE_ACCOUNT_UUID = "abc-123-def-456"
SAMPLE_CLIENT_ID = "dt0s01.TESTCLIENT"
SAMPLE_CLIENT_SECRET = "dt0s01.TESTCLIENT.TESTSECRET"


@pytest.fixture
def sample_config() -> Config:
    """Create a sample configuration for testing."""
    config = Config()
    config.current_context = "test"
    config.contexts = [
        NamedContext(
            name="test",
            context=Context(
                account_uuid=SAMPLE_ACCOUNT_UUID,
                credentials_ref="test-creds",
            ),
        )
    ]
    config.credentials = [
        NamedCredential(
            name="test-creds",
            credential=Credential(
                client_id=SAMPLE_CLIENT_ID,
                client_secret=SAMPLE_CLIENT_SECRET,
            ),
        )
    ]
    return config


@pytest.fixture
def mock_token_manager():
    """Create a mock token manager that returns a valid token."""
    with patch("dtiam.utils.auth.TokenManager") as mock_class:
        mock_instance = MagicMock()
        mock_instance.get_headers.return_value = {"Authorization": "Bearer test-token"}
        mock_instance.is_token_valid.return_value = True
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_client(mock_token_manager) -> Client:
    """Create a mock client for testing."""
    client = Client(
        account_uuid=SAMPLE_ACCOUNT_UUID,
        token_manager=mock_token_manager,
        timeout=30.0,
        verbose=False,
    )
    return client


class MockResponse:
    """Mock httpx response for testing."""

    def __init__(
        self,
        json_data: Any = None,
        status_code: int = 200,
        text: str = "",
    ):
        self._json_data = json_data
        self.status_code = status_code
        self._text = text or json.dumps(json_data) if json_data else ""

    def json(self) -> Any:
        return self._json_data

    @property
    def text(self) -> str:
        return self._text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=MagicMock(),
                response=self,
            )


@pytest.fixture
def mock_response():
    """Factory fixture for creating mock responses."""
    def _create_response(json_data: Any = None, status_code: int = 200):
        return MockResponse(json_data=json_data, status_code=status_code)
    return _create_response


# Sample API responses
@pytest.fixture
def sample_groups() -> list[dict[str, Any]]:
    """Sample groups response."""
    return [
        {
            "uuid": "group-uuid-1",
            "name": "DevOps Team",
            "description": "DevOps engineering team",
            "owner": "LOCAL",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-15T00:00:00Z",
        },
        {
            "uuid": "group-uuid-2",
            "name": "Platform Team",
            "description": "Platform engineering team",
            "owner": "LOCAL",
            "createdAt": "2024-01-02T00:00:00Z",
            "updatedAt": "2024-01-16T00:00:00Z",
        },
    ]


@pytest.fixture
def sample_users() -> list[dict[str, Any]]:
    """Sample users response."""
    return [
        {
            "uid": "user-uid-1",
            "email": "admin@example.com",
            "name": "Admin",
            "surname": "User",
            "userStatus": "ACTIVE",
        },
        {
            "uid": "user-uid-2",
            "email": "developer@example.com",
            "name": "Developer",
            "surname": "User",
            "userStatus": "ACTIVE",
        },
    ]


@pytest.fixture
def sample_policies() -> list[dict[str, Any]]:
    """Sample policies response."""
    return [
        {
            "uuid": "policy-uuid-1",
            "name": "admin-policy",
            "description": "Full admin access",
            "statementQuery": "ALLOW settings:objects:read; ALLOW settings:objects:write;",
        },
        {
            "uuid": "policy-uuid-2",
            "name": "viewer-policy",
            "description": "Read-only access",
            "statementQuery": "ALLOW settings:objects:read;",
        },
    ]


@pytest.fixture
def sample_bindings() -> list[dict[str, Any]]:
    """Sample bindings response."""
    return [
        {
            "policyUuid": "policy-uuid-1",
            "groups": ["group-uuid-1"],
            "boundaries": [],
        },
        {
            "policyUuid": "policy-uuid-2",
            "groups": ["group-uuid-2"],
            "boundaries": ["boundary-uuid-1"],
        },
    ]


@pytest.fixture
def sample_boundaries() -> list[dict[str, Any]]:
    """Sample boundaries response."""
    return [
        {
            "uuid": "boundary-uuid-1",
            "name": "production-boundary",
            "boundaryQuery": "environment.tag.equals('production')",
        },
    ]


@pytest.fixture
def sample_environments() -> list[dict[str, Any]]:
    """Sample environments response."""
    return [
        {
            "id": "env-id-1",
            "name": "Production",
        },
        {
            "id": "env-id-2",
            "name": "Staging",
        },
    ]


@pytest.fixture
def sample_service_users() -> list[dict[str, Any]]:
    """Sample service users response."""
    return [
        {
            "uid": "service-user-uid-1",
            "name": "CI Pipeline",
            "description": "CI/CD automation",
            "groups": ["group-uuid-1"],
        },
    ]


@pytest.fixture
def sample_limits() -> list[dict[str, Any]]:
    """Sample account limits response."""
    return [
        {"name": "maxUsers", "current": 50, "max": 100},
        {"name": "maxGroups", "current": 25, "max": 50},
        {"name": "maxPolicies", "current": 10, "max": 100},
    ]


@pytest.fixture
def sample_subscriptions() -> list[dict[str, Any]]:
    """Sample subscriptions response."""
    return [
        {
            "uuid": "sub-uuid-1",
            "name": "Enterprise",
            "type": "ENTERPRISE",
            "status": "ACTIVE",
            "startTime": "2024-01-01T00:00:00Z",
            "endTime": "2025-01-01T00:00:00Z",
        },
    ]


@pytest.fixture
def sample_zones() -> list[dict[str, Any]]:
    """Sample management zones response."""
    return [
        {
            "id": "zone-1",
            "name": "Production",
            "rules": [],
        },
        {
            "id": "zone-2",
            "name": "Staging",
            "rules": [],
        },
        {
            "id": "zone-3",
            "name": "Development",
            "rules": [],
        },
    ]

