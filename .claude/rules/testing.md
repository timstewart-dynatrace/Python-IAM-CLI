# Testing Conventions

This document defines testing standards and conventions for the dtiam project.

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_client.py -v

# Run with coverage
pytest tests/ -v --cov=src/dtiam --cov-report=term-missing

# Run tests matching a pattern
pytest tests/ -v -k "test_api"
```

## Test Structure

### File Organization

```
tests/
├── __init__.py
├── conftest.py           # Shared fixtures
├── test_cli.py           # CLI integration tests
├── test_client.py        # HTTP client tests
├── test_config.py        # Configuration tests
├── test_output.py        # Output formatting tests
├── test_resources.py     # Resource handler tests
└── test_utils.py         # Utility function tests
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Test files | `test_*.py` | `test_client.py` |
| Test classes | `Test*` | `TestClient` |
| Test methods | `test_*` | `test_get_user_by_email` |
| Fixtures | descriptive_name | `mock_token_manager` |

## Writing Tests

### Test Class Structure

Group related tests in classes:

```python
class TestGroupHandler:
    """Tests for GroupHandler class."""

    @pytest.fixture
    def handler(self, mock_client):
        """Create handler for testing."""
        return GroupHandler(mock_client)

    def test_list_groups(self, handler):
        """Test listing all groups."""
        # Arrange
        # Act
        # Assert

    def test_get_group_by_uuid(self, handler):
        """Test getting group by UUID."""
        pass

    def test_get_group_not_found_falls_back_to_list(self, handler):
        """Test 404 fallback to list filtering."""
        pass
```

### Fixtures

Use fixtures for common test setup:

```python
# conftest.py
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_token_manager():
    """Create a mock token manager."""
    manager = MagicMock()
    manager.get_headers.return_value = {"Authorization": "Bearer test-token"}
    return manager

@pytest.fixture
def mock_client(mock_token_manager):
    """Create a mock API client."""
    from dtiam.client import Client
    return Client(
        account_uuid="test-account",
        token_manager=mock_token_manager,
    )

@pytest.fixture
def sample_group():
    """Return sample group data."""
    return {
        "uuid": "abc-123",
        "name": "Test Group",
        "description": "A test group",
    }
```

### Mocking

Use `unittest.mock` for mocking:

```python
from unittest.mock import MagicMock, patch

def test_request_success(self, client):
    """Test successful request."""
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.status_code = 200

    with patch.object(client._client, "request") as mock_request:
        mock_request.return_value = mock_response

        response = client.get("/groups")

        assert response == mock_response
        mock_request.assert_called_once()
```

### Testing API Errors

Test error handling paths:

```python
def test_get_group_404_falls_back_to_list(self, handler):
    """Test that 404 error falls back to list filtering."""
    # Mock direct GET to return 404
    handler.client.get.side_effect = [
        APIError("Not found", status_code=404),
    ]

    # Mock list to return groups
    with patch.object(handler, "list") as mock_list:
        mock_list.return_value = [
            {"uuid": "abc-123", "name": "Group 1"},
            {"uuid": "def-456", "name": "Group 2"},
        ]

        result = handler.get("abc-123")

        assert result["name"] == "Group 1"
        mock_list.assert_called_once()
```

### Testing CLI Commands

Use Typer's test runner:

```python
from typer.testing import CliRunner
from dtiam.cli import app

runner = CliRunner()

def test_get_groups_command():
    """Test get groups command."""
    with patch("dtiam.commands.get.create_client_from_config") as mock_client:
        mock_client.return_value = MagicMock()

        result = runner.invoke(app, ["get", "groups"])

        assert result.exit_code == 0
```

## Test Categories

### Unit Tests

Test individual functions/methods in isolation:

```python
def test_mask_secret_basic():
    """Test basic secret masking."""
    result = mask_secret("dt0s01.ABCDEF.GHIJKLMN")
    assert result == "dt0s****KLMN"

def test_mask_secret_short():
    """Test masking short secrets."""
    result = mask_secret("short")
    assert result == "*****"
```

### Integration Tests

Test component interactions:

```python
def test_client_authentication_flow():
    """Test OAuth2 token acquisition."""
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = MagicMock(
            is_success=True,
            json=lambda: {"access_token": "token", "expires_in": 300},
        )

        manager = TokenManager(
            client_id="test-id",
            client_secret="test-secret",
            account_uuid="test-account",
        )

        token = manager.get_token()

        assert token == "token"
```

### Error Tests

Test error conditions explicitly:

```python
def test_create_client_no_context_raises():
    """Test error when no context is configured."""
    config = Config()  # Empty config

    with patch("dtiam.client.get_env_override") as mock_env:
        mock_env.return_value = None

        with pytest.raises(RuntimeError, match="No authentication configured"):
            create_client_from_config(config=config)
```

## Best Practices

1. **Test one thing per test** - Each test should verify one behavior
2. **Use descriptive names** - Test name should describe what's being tested
3. **Arrange-Act-Assert** - Structure tests clearly
4. **Don't test implementation details** - Test behavior, not internal structure
5. **Keep tests fast** - Mock external dependencies
6. **Test edge cases** - Empty lists, None values, error conditions

## Coverage Requirements

- Aim for >80% code coverage
- All public APIs should have tests
- Error handling paths should be tested
- New features require tests before merge
