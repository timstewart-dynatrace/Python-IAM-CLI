"""Tests for the config module."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from dtiam.config import (
    Config,
    Context,
    Credential,
    NamedContext,
    NamedCredential,
    load_config,
    save_config,
    get_env_override,
    get_config_path,
)


class TestCredential:
    """Tests for Credential model."""

    def test_create_credential(self):
        """Test creating a credential."""
        cred = Credential(
            **{"client-id": "dt0s01.TEST", "client-secret": "dt0s01.TEST.SECRET"}
        )
        assert cred.client_id == "dt0s01.TEST"
        assert cred.client_secret == "dt0s01.TEST.SECRET"

    def test_credential_to_dict(self):
        """Test converting credential to dict."""
        cred = Credential(
            **{"client-id": "dt0s01.TEST", "client-secret": "dt0s01.TEST.SECRET"}
        )
        data = cred.model_dump(by_alias=True)
        assert data["client-id"] == "dt0s01.TEST"
        assert data["client-secret"] == "dt0s01.TEST.SECRET"

    def test_credential_with_aliases(self):
        """Test credential works with both alias and field names."""
        # Using aliases
        cred1 = Credential(**{"client-id": "id1", "client-secret": "secret1"})
        assert cred1.client_id == "id1"

        # Using field names
        cred2 = Credential(client_id="id2", client_secret="secret2")
        assert cred2.client_id == "id2"


class TestContext:
    """Tests for Context model."""

    def test_create_context(self):
        """Test creating a context."""
        ctx = Context(
            **{"account-uuid": "abc-123", "credentials-ref": "prod-creds"}
        )
        assert ctx.account_uuid == "abc-123"
        assert ctx.credentials_ref == "prod-creds"

    def test_context_to_dict(self):
        """Test converting context to dict."""
        ctx = Context(
            **{"account-uuid": "abc-123", "credentials-ref": "prod-creds"}
        )
        data = ctx.model_dump(by_alias=True)
        assert data["account-uuid"] == "abc-123"
        assert data["credentials-ref"] == "prod-creds"


class TestNamedCredential:
    """Tests for NamedCredential model."""

    def test_create_named_credential(self):
        """Test creating a named credential."""
        cred = Credential(client_id="id", client_secret="secret")
        named = NamedCredential(name="test-creds", credential=cred)
        assert named.name == "test-creds"
        assert named.credential.client_id == "id"


class TestNamedContext:
    """Tests for NamedContext model."""

    def test_create_named_context(self):
        """Test creating a named context."""
        ctx = Context(account_uuid="abc-123", credentials_ref="creds")
        named = NamedContext(name="prod", context=ctx)
        assert named.name == "prod"
        assert named.context.account_uuid == "abc-123"


class TestConfig:
    """Tests for Config model."""

    def test_create_empty_config(self):
        """Test creating an empty config."""
        config = Config()
        assert config.api_version == "v1"
        assert config.kind == "Config"
        assert config.current_context == ""
        assert config.contexts == []
        assert config.credentials == []

    def test_set_credential(self):
        """Test setting a credential."""
        config = Config()
        config.set_credential(
            name="new-creds",
            client_id="dt0s01.NEW",
            client_secret="dt0s01.NEW.SECRET",
        )
        cred = config.get_credential("new-creds")
        assert cred is not None
        assert cred.client_id == "dt0s01.NEW"

    def test_set_context(self):
        """Test setting a context."""
        config = Config()
        config.set_context(
            name="new-context",
            account_uuid="xyz-789",
            credentials_ref="new-creds",
        )
        ctx = config.get_context("new-context")
        assert ctx is not None
        assert ctx.account_uuid == "xyz-789"

    def test_get_current_context(self):
        """Test getting current context."""
        config = Config()
        config.set_context(
            name="test",
            account_uuid="abc-123",
            credentials_ref="test-creds",
        )
        config.current_context = "test"

        ctx = config.get_current_context()
        assert ctx is not None
        assert ctx.account_uuid == "abc-123"

    def test_get_current_context_none(self):
        """Test getting current context when none set."""
        config = Config()
        ctx = config.get_current_context()
        assert ctx is None

    def test_get_credential(self):
        """Test getting a credential by name."""
        config = Config()
        config.set_credential("test-creds", "client-id", "secret")
        cred = config.get_credential("test-creds")
        assert cred is not None
        assert cred.client_id == "client-id"

    def test_get_credential_not_found(self):
        """Test getting a non-existent credential."""
        config = Config()
        cred = config.get_credential("nonexistent")
        assert cred is None

    def test_update_existing_credential(self):
        """Test updating an existing credential."""
        config = Config()
        config.set_credential("test-creds", "old-id", "old-secret")
        config.set_credential("test-creds", "new-id", "new-secret")

        cred = config.get_credential("test-creds")
        assert cred is not None
        assert cred.client_id == "new-id"
        # Should still only have one credential
        assert len(config.credentials) == 1

    def test_update_existing_context(self):
        """Test updating an existing context."""
        config = Config()
        config.set_context("test", "uuid-1", "creds-1")
        config.set_context("test", account_uuid="uuid-2")

        ctx = config.get_context("test")
        assert ctx is not None
        assert ctx.account_uuid == "uuid-2"
        # Should still only have one context
        assert len(config.contexts) == 1

    def test_delete_context(self):
        """Test deleting a context."""
        config = Config()
        config.set_context("test", "uuid", "creds")
        assert config.delete_context("test") is True
        assert config.get_context("test") is None

    def test_delete_context_not_found(self):
        """Test deleting a non-existent context."""
        config = Config()
        assert config.delete_context("nonexistent") is False

    def test_delete_credential(self):
        """Test deleting a credential."""
        config = Config()
        config.set_credential("test", "id", "secret")
        assert config.delete_credential("test") is True
        assert config.get_credential("test") is None


class TestConfigIO:
    """Tests for config loading and saving."""

    def test_save_and_load_config(self):
        """Test saving and loading config."""
        config = Config()
        config.set_credential("test-creds", "dt0s01.TEST", "dt0s01.TEST.SECRET")
        config.set_context("test", "abc-123", "test-creds")
        config.current_context = "test"

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"

            # Temporarily override the config path
            with patch_config_path(config_path):
                save_config(config)
                assert config_path.exists()

                loaded = load_config()
                assert loaded.current_context == "test"
                assert len(loaded.contexts) == 1
                assert len(loaded.credentials) == 1

    def test_load_nonexistent_config(self):
        """Test loading a config that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent"

            with patch_config_path(config_path):
                config = load_config()
                # Should return empty config
                assert config.current_context == ""
                assert config.contexts == []

    def test_config_yaml_format(self):
        """Test that config is saved in expected YAML format."""
        config = Config()
        config.set_credential("test-creds", "dt0s01.TEST", "dt0s01.TEST.SECRET")
        config.set_context("test", "abc-123", "test-creds")
        config.current_context = "test"

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"

            with patch_config_path(config_path):
                save_config(config)

                with open(config_path) as f:
                    data = yaml.safe_load(f)

                assert data["api-version"] == "v1"
                assert data["kind"] == "Config"
                assert data["current-context"] == "test"
                assert len(data["contexts"]) == 1
                assert len(data["credentials"]) == 1


class TestEnvOverride:
    """Tests for environment variable overrides."""

    def test_get_env_override_context(self):
        """Test getting context from environment."""
        os.environ["DTIAM_CONTEXT"] = "env-context"
        try:
            result = get_env_override("context")
            assert result == "env-context"
        finally:
            del os.environ["DTIAM_CONTEXT"]

    def test_get_env_override_client_id(self):
        """Test getting client ID from environment."""
        os.environ["DTIAM_CLIENT_ID"] = "env-client-id"
        try:
            result = get_env_override("client_id")
            assert result == "env-client-id"
        finally:
            del os.environ["DTIAM_CLIENT_ID"]

    def test_get_env_override_not_set(self):
        """Test getting env override when not set."""
        # Ensure it's not set
        os.environ.pop("DTIAM_CONTEXT", None)
        result = get_env_override("context")
        assert result is None


# Helper for patching config path in tests
class patch_config_path:
    """Context manager to temporarily override config path."""

    def __init__(self, path: Path):
        self.path = path
        self.original = None

    def __enter__(self):
        import dtiam.config as config_module
        self.original = config_module.get_config_path
        config_module.get_config_path = lambda: self.path
        return self

    def __exit__(self, *args):
        import dtiam.config as config_module
        config_module.get_config_path = self.original

