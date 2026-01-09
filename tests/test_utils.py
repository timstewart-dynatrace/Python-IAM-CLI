"""Tests for utility modules."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from dtiam.utils.auth import TokenManager, TokenInfo, OAuthError, IAM_SCOPES
from dtiam.utils.resolver import ResourceResolver, is_uuid, is_likely_id
from dtiam.utils.cache import Cache, CacheEntry, cached
from dtiam.utils.templates import TemplateRenderer, TemplateManager, TemplateError


class TestTokenInfo:
    """Tests for TokenInfo dataclass."""

    def test_create_token_info(self):
        """Test creating TokenInfo."""
        token = TokenInfo(
            access_token="test-token",
            expires_at=time.time() + 300,
            scope="test-scope",
        )
        assert token.access_token == "test-token"
        assert token.scope == "test-scope"


class TestOAuthError:
    """Tests for OAuthError exception."""

    def test_oauth_error_basic(self):
        """Test basic OAuthError."""
        error = OAuthError("Test error")
        assert str(error) == "Test error"
        assert error.error_code is None
        assert error.error_description is None

    def test_oauth_error_with_details(self):
        """Test OAuthError with error code and description."""
        error = OAuthError(
            "Test error",
            error_code="invalid_grant",
            error_description="The credentials are invalid",
        )
        assert error.error_code == "invalid_grant"
        assert error.error_description == "The credentials are invalid"


class TestTokenManager:
    """Tests for TokenManager class."""

    def test_create_token_manager(self):
        """Test creating TokenManager."""
        manager = TokenManager(
            client_id="test-client",
            client_secret="test-secret",
            account_uuid="test-account",
        )
        assert manager.client_id == "test-client"
        assert manager.client_secret == "test-secret"
        assert manager.account_uuid == "test-account"
        assert manager.scope == IAM_SCOPES

    def test_token_manager_custom_scope(self):
        """Test TokenManager with custom scope."""
        manager = TokenManager(
            client_id="test-client",
            client_secret="test-secret",
            account_uuid="test-account",
            scope="custom-scope",
        )
        assert manager.scope == "custom-scope"

    def test_is_token_valid_no_token(self):
        """Test is_token_valid with no cached token."""
        manager = TokenManager(
            client_id="test",
            client_secret="test",
            account_uuid="test",
        )
        assert manager.is_token_valid() is False

    def test_is_token_valid_expired(self):
        """Test is_token_valid with expired token."""
        manager = TokenManager(
            client_id="test",
            client_secret="test",
            account_uuid="test",
        )
        manager._token = TokenInfo(
            access_token="test",
            expires_at=time.time() - 100,  # Expired
            scope="test",
        )
        assert manager.is_token_valid() is False

    def test_is_token_valid_valid(self):
        """Test is_token_valid with valid token."""
        manager = TokenManager(
            client_id="test",
            client_secret="test",
            account_uuid="test",
        )
        manager._token = TokenInfo(
            access_token="test",
            expires_at=time.time() + 300,  # Valid for 5 minutes
            scope="test",
        )
        assert manager.is_token_valid() is True

    def test_clear_cache(self):
        """Test clearing token cache."""
        manager = TokenManager(
            client_id="test",
            client_secret="test",
            account_uuid="test",
        )
        manager._token = TokenInfo(
            access_token="test",
            expires_at=time.time() + 300,
            scope="test",
        )
        manager.clear_cache()
        assert manager._token is None

    def test_get_headers(self):
        """Test get_headers returns proper format."""
        manager = TokenManager(
            client_id="test",
            client_secret="test",
            account_uuid="test",
        )
        manager._token = TokenInfo(
            access_token="my-token",
            expires_at=time.time() + 300,
            scope="test",
        )
        headers = manager.get_headers()
        assert headers["Authorization"] == "Bearer my-token"
        assert headers["Accept"] == "application/json"


class TestIsUuid:
    """Tests for is_uuid function."""

    def test_valid_uuid(self):
        """Test with valid UUID."""
        assert is_uuid("12345678-1234-1234-1234-123456789abc") is True
        assert is_uuid("ABCDEF12-3456-7890-ABCD-EF1234567890") is True

    def test_invalid_uuid(self):
        """Test with invalid UUID."""
        assert is_uuid("not-a-uuid") is False
        assert is_uuid("12345678") is False
        assert is_uuid("") is False
        assert is_uuid("12345678-1234-1234-1234-123456789") is False


class TestIsLikelyId:
    """Tests for is_likely_id function."""

    def test_uuid_is_likely_id(self):
        """Test UUID is considered likely ID."""
        assert is_likely_id("12345678-1234-1234-1234-123456789abc") is True

    def test_short_hex_is_likely_id(self):
        """Test short hex string is considered likely ID."""
        assert is_likely_id("1234567890abcdef1234") is True

    def test_name_is_not_likely_id(self):
        """Test human-readable name is not considered ID."""
        assert is_likely_id("DevOps Team") is False
        assert is_likely_id("My Group Name") is False

    def test_short_string_not_likely_id(self):
        """Test short string is not considered ID."""
        assert is_likely_id("abc") is False


class TestResourceResolver:
    """Tests for ResourceResolver class."""

    def test_resolve_group_by_uuid(self):
        """Test resolving group by UUID."""
        mock_client = MagicMock()
        resolver = ResourceResolver(mock_client)

        with patch("dtiam.resources.groups.GroupHandler") as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler.get.return_value = {"uuid": "test-uuid", "name": "Test"}
            mock_handler_class.return_value = mock_handler

            result = resolver.resolve_group("12345678-1234-1234-1234-123456789abc")
            assert result == "test-uuid"

    def test_resolve_group_by_name(self):
        """Test resolving group by name."""
        mock_client = MagicMock()
        resolver = ResourceResolver(mock_client)

        with patch("dtiam.resources.groups.GroupHandler") as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler.get_by_name.return_value = {"uuid": "resolved-uuid", "name": "Test Group"}
            mock_handler_class.return_value = mock_handler

            result = resolver.resolve_group("Test Group")
            assert result == "resolved-uuid"

    def test_resolve_group_not_found(self):
        """Test resolving non-existent group."""
        mock_client = MagicMock()
        resolver = ResourceResolver(mock_client)

        with patch("dtiam.resources.groups.GroupHandler") as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler.get_by_name.return_value = None
            mock_handler_class.return_value = mock_handler

            with pytest.raises(ValueError, match="Group not found"):
                resolver.resolve_group("Nonexistent Group")

    def test_resolve_user_by_email(self):
        """Test resolving user by email."""
        mock_client = MagicMock()
        resolver = ResourceResolver(mock_client)

        with patch("dtiam.resources.users.UserHandler") as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler.get_by_email.return_value = {"uid": "user-uid", "email": "test@example.com"}
            mock_handler_class.return_value = mock_handler

            result = resolver.resolve_user("test@example.com")
            assert result == "user-uid"


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_create_cache_entry(self):
        """Test creating CacheEntry."""
        entry = CacheEntry(
            value={"test": "data"},
            expires_at=time.time() + 300,
        )
        assert entry.value == {"test": "data"}
        assert entry.created_at <= time.time()


class TestCache:
    """Tests for Cache class."""

    @pytest.fixture
    def fresh_cache(self):
        """Create a fresh cache instance for testing."""
        # Reset singleton for testing
        Cache._instance = None
        cache = Cache()
        cache._init()  # Ensure fresh state
        return cache

    def test_cache_singleton(self, fresh_cache):
        """Test Cache is a singleton."""
        cache1 = Cache()
        cache2 = Cache()
        assert cache1 is cache2

    def test_cache_set_and_get(self, fresh_cache):
        """Test setting and getting cache values."""
        fresh_cache.set("test-key", {"value": 123})
        result = fresh_cache.get("test-key")
        assert result == {"value": 123}

    def test_cache_get_missing(self, fresh_cache):
        """Test getting non-existent key."""
        result = fresh_cache.get("nonexistent")
        assert result is None

    def test_cache_expiration(self, fresh_cache):
        """Test cache entry expiration."""
        fresh_cache.set("expires-soon", "value", ttl=1)
        assert fresh_cache.get("expires-soon") == "value"

        # Wait for expiration
        time.sleep(1.1)
        assert fresh_cache.get("expires-soon") is None

    def test_cache_delete(self, fresh_cache):
        """Test deleting cache entry."""
        fresh_cache.set("to-delete", "value")
        assert fresh_cache.delete("to-delete") is True
        assert fresh_cache.get("to-delete") is None
        assert fresh_cache.delete("to-delete") is False

    def test_cache_clear(self, fresh_cache):
        """Test clearing all cache entries."""
        fresh_cache.set("key1", "value1")
        fresh_cache.set("key2", "value2")
        count = fresh_cache.clear()
        assert count == 2
        assert fresh_cache.get("key1") is None
        assert fresh_cache.get("key2") is None

    def test_cache_clear_expired(self, fresh_cache):
        """Test clearing only expired entries."""
        fresh_cache.set("valid", "value", ttl=300)
        fresh_cache.set("expired", "value", ttl=0)

        # Manually expire the entry
        fresh_cache._cache["expired"].expires_at = time.time() - 1

        count = fresh_cache.clear_expired()
        assert count == 1
        assert fresh_cache.get("valid") == "value"

    def test_cache_clear_prefix(self, fresh_cache):
        """Test clearing entries by prefix."""
        fresh_cache.set("groups:1", "value1")
        fresh_cache.set("groups:2", "value2")
        fresh_cache.set("users:1", "value3")

        count = fresh_cache.clear_prefix("groups:")
        assert count == 2
        assert fresh_cache.get("groups:1") is None
        assert fresh_cache.get("users:1") == "value3"

    def test_cache_stats(self, fresh_cache):
        """Test cache statistics."""
        fresh_cache.set("key1", "value1")
        fresh_cache.get("key1")  # Hit
        fresh_cache.get("missing")  # Miss

        stats = fresh_cache.stats()
        assert stats["total_entries"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0

    def test_cache_keys(self, fresh_cache):
        """Test listing cache keys."""
        fresh_cache.set("key1", "value1")
        fresh_cache.set("key2", "value2")

        keys = fresh_cache.keys()
        assert "key1" in keys
        assert "key2" in keys

    def test_cache_default_ttl(self, fresh_cache):
        """Test default TTL setting."""
        assert fresh_cache.default_ttl == 300
        fresh_cache.default_ttl = 600
        assert fresh_cache.default_ttl == 600


class TestCachedDecorator:
    """Tests for the cached decorator."""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Reset cache before each test."""
        Cache._instance = None

    def test_cached_function(self):
        """Test cached decorator caches results."""
        call_count = 0

        @cached(ttl=300)
        def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - should be cached
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # No additional call

        # Different argument - not cached
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2


class TestTemplateRenderer:
    """Tests for TemplateRenderer class."""

    def test_render_simple_string(self):
        """Test rendering a simple template string."""
        renderer = TemplateRenderer({"name": "Test"})
        result = renderer.render_string("Hello {{ name }}!")
        assert result == "Hello Test!"

    def test_render_multiple_variables(self):
        """Test rendering with multiple variables."""
        renderer = TemplateRenderer({"first": "John", "last": "Doe"})
        result = renderer.render_string("{{ first }} {{ last }}")
        assert result == "John Doe"

    def test_render_with_default(self):
        """Test rendering with default value."""
        renderer = TemplateRenderer({})
        result = renderer.render_string("Hello {{ name | default('World') }}!")
        assert result == "Hello World!"

    def test_render_missing_required_variable(self):
        """Test rendering with missing required variable."""
        renderer = TemplateRenderer({})
        with pytest.raises(TemplateError, match="Missing required template variables"):
            renderer.render_string("Hello {{ name }}!")

    def test_render_dict(self):
        """Test rendering a dictionary."""
        renderer = TemplateRenderer({"team": "DevOps"})
        data = {"name": "team-{{ team }}", "description": "The {{ team }} team"}
        result = renderer.render_dict(data)
        assert result["name"] == "team-DevOps"
        assert result["description"] == "The DevOps team"

    def test_render_list(self):
        """Test rendering a list."""
        renderer = TemplateRenderer({"env": "prod"})
        data = ["{{ env }}-server", "{{ env }}-db"]
        result = renderer.render_list(data)
        assert result == ["prod-server", "prod-db"]

    def test_get_variables(self):
        """Test extracting variables from template."""
        renderer = TemplateRenderer()
        template = "{{ name }} - {{ value | default('none') }}"
        variables = renderer.get_variables(template)

        assert len(variables) == 2
        assert {"name": "name"} in variables
        assert {"name": "value", "default": "none"} in variables


class TestTemplateManager:
    """Tests for TemplateManager class."""

    def test_list_builtin_templates(self):
        """Test listing built-in templates."""
        manager = TemplateManager()
        templates = manager.list_templates(include_builtin=True)

        # Should have several built-in templates
        names = [t["name"] for t in templates]
        assert "group-basic" in names
        assert "group-team" in names
        assert "policy-readonly" in names

    def test_get_builtin_template(self):
        """Test getting a built-in template."""
        manager = TemplateManager()
        template = manager.get_template("group-basic")

        assert template is not None
        assert template["kind"] == "Group"
        assert "template" in template

    def test_get_nonexistent_template(self):
        """Test getting a non-existent template."""
        manager = TemplateManager()
        template = manager.get_template("nonexistent-template")
        assert template is None

    def test_get_template_variables(self):
        """Test extracting variables from a template."""
        manager = TemplateManager()
        variables = manager.get_template_variables("group-basic")

        # group-basic should have group_name and description variables
        names = [v["name"] for v in variables]
        assert "group_name" in names

    def test_render_template(self):
        """Test rendering a template."""
        manager = TemplateManager()
        result = manager.render_template(
            "group-basic",
            {"group_name": "My Team", "description": "My team description"},
        )

        assert result["kind"] == "Group"
        assert result["spec"]["name"] == "My Team"
        assert result["spec"]["description"] == "My team description"

    def test_render_template_not_found(self):
        """Test rendering non-existent template."""
        manager = TemplateManager()
        with pytest.raises(TemplateError, match="Template not found"):
            manager.render_template("nonexistent", {})

    def test_render_template_missing_variables(self):
        """Test rendering template with missing required variables."""
        manager = TemplateManager()
        with pytest.raises(TemplateError, match="Missing required"):
            manager.render_template("group-basic", {})

    def test_delete_builtin_template(self):
        """Test that built-in templates cannot be deleted."""
        manager = TemplateManager()
        result = manager.delete_template("group-basic")
        assert result is False

        # Template should still exist
        template = manager.get_template("group-basic")
        assert template is not None

