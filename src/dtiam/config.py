"""Configuration management for dtiam.

Handles multi-context configuration, OAuth2 credential storage, and XDG Base Directory compliance.
Configuration is stored in YAML format at ~/.config/dtiam/config (or XDG_CONFIG_HOME).
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from platformdirs import user_config_dir
from pydantic import BaseModel, Field


class Credential(BaseModel):
    """OAuth2 credential pair for Dynatrace Account API."""

    client_id: str = Field(alias="client-id", description="OAuth2 client ID")
    client_secret: str = Field(alias="client-secret", description="OAuth2 client secret")

    model_config = {"populate_by_name": True}


class NamedCredential(BaseModel):
    """A named credential entry."""

    name: str
    credential: Credential


class Context(BaseModel):
    """A named context containing account UUID and credential reference."""

    account_uuid: str = Field(alias="account-uuid", description="Dynatrace account UUID")
    credentials_ref: str = Field(
        alias="credentials-ref", description="Reference to a named credential"
    )

    model_config = {"populate_by_name": True}


class NamedContext(BaseModel):
    """A context with its name."""

    name: str
    context: Context


class Preferences(BaseModel):
    """User preferences for output and editor."""

    output: str = Field(default="table", description="Default output format")
    editor: str = Field(default="vim", description="Default editor for edit commands")


class Config(BaseModel):
    """Root configuration structure matching kubectl-style config."""

    api_version: str = Field(default="v1", alias="api-version")
    kind: str = Field(default="Config")
    current_context: str = Field(default="", alias="current-context")
    contexts: list[NamedContext] = Field(default_factory=list)
    credentials: list[NamedCredential] = Field(default_factory=list)
    preferences: Preferences = Field(default_factory=Preferences)

    model_config = {"populate_by_name": True}

    def get_context(self, name: str) -> Context | None:
        """Get a context by name."""
        for ctx in self.contexts:
            if ctx.name == name:
                return ctx.context
        return None

    def get_current_context(self) -> Context | None:
        """Get the currently active context."""
        if not self.current_context:
            return None
        return self.get_context(self.current_context)

    def get_credential(self, name: str) -> Credential | None:
        """Get a credential by name."""
        for c in self.credentials:
            if c.name == name:
                return c.credential
        return None

    def get_current_credential(self) -> Credential | None:
        """Get the credential for the current context."""
        ctx = self.get_current_context()
        if not ctx:
            return None
        return self.get_credential(ctx.credentials_ref)

    def set_context(
        self,
        name: str,
        account_uuid: str | None = None,
        credentials_ref: str | None = None,
    ) -> None:
        """Create or update a context."""
        existing = None
        for i, ctx in enumerate(self.contexts):
            if ctx.name == name:
                existing = i
                break

        if existing is not None:
            ctx = self.contexts[existing].context
            if account_uuid:
                ctx.account_uuid = account_uuid
            if credentials_ref:
                ctx.credentials_ref = credentials_ref
        else:
            if not account_uuid or not credentials_ref:
                raise ValueError("New context requires both account-uuid and credentials-ref")
            self.contexts.append(
                NamedContext(
                    name=name,
                    context=Context(
                        **{"account-uuid": account_uuid, "credentials-ref": credentials_ref}
                    ),
                )
            )

    def set_credential(self, name: str, client_id: str, client_secret: str) -> None:
        """Create or update a credential."""
        for c in self.credentials:
            if c.name == name:
                c.credential.client_id = client_id
                c.credential.client_secret = client_secret
                return
        self.credentials.append(
            NamedCredential(
                name=name,
                credential=Credential(**{"client-id": client_id, "client-secret": client_secret}),
            )
        )

    def delete_context(self, name: str) -> bool:
        """Delete a context by name. Returns True if deleted."""
        for i, ctx in enumerate(self.contexts):
            if ctx.name == name:
                self.contexts.pop(i)
                if self.current_context == name:
                    self.current_context = ""
                return True
        return False

    def delete_credential(self, name: str) -> bool:
        """Delete a credential by name. Returns True if deleted."""
        for i, c in enumerate(self.credentials):
            if c.name == name:
                self.credentials.pop(i)
                return True
        return False


def get_config_dir() -> Path:
    """Get the configuration directory path (XDG compliant)."""
    return Path(user_config_dir("dtiam", appauthor=False))


def get_config_path() -> Path:
    """Get the configuration file path."""
    return get_config_dir() / "config"


def get_legacy_config_path() -> Path:
    """Get the legacy configuration path (~/.dtiam/config)."""
    return Path.home() / ".dtiam" / "config"


def migrate_legacy_config() -> bool:
    """Migrate legacy config to XDG location if needed. Returns True if migrated."""
    legacy_path = get_legacy_config_path()
    new_path = get_config_path()

    if legacy_path.exists() and not new_path.exists():
        new_path.parent.mkdir(parents=True, exist_ok=True)
        new_path.write_text(legacy_path.read_text())
        return True
    return False


def load_config() -> Config:
    """Load configuration from file, creating default if not exists."""
    migrate_legacy_config()

    config_path = get_config_path()

    if not config_path.exists():
        return Config()

    try:
        data = yaml.safe_load(config_path.read_text())
        if data is None:
            return Config()
        return Config.model_validate(data)
    except Exception as e:
        raise RuntimeError(f"Failed to load config from {config_path}: {e}") from e


def save_config(config: Config) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict with proper aliases for YAML output
    data = config.model_dump(by_alias=True, exclude_none=True)

    config_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def get_env_override(key: str) -> str | None:
    """Get environment variable override for a config key.

    Supported environment variables:
    - DTIAM_CONTEXT: Override current context name
    - DTIAM_OUTPUT: Default output format
    - DTIAM_VERBOSE: Enable verbose mode
    - DTIAM_CLIENT_ID: OAuth2 client ID (use with DTIAM_CLIENT_SECRET)
    - DTIAM_CLIENT_SECRET: OAuth2 client secret (use with DTIAM_CLIENT_ID)
    - DTIAM_ACCOUNT_UUID: Dynatrace account UUID
    - DTIAM_BEARER_TOKEN: Static bearer token (alternative to OAuth2)
    - DTIAM_ENVIRONMENT_TOKEN: Environment API token for management zones (optional)

    Note: DTIAM_BEARER_TOKEN takes precedence over OAuth2 credentials.
    Bearer tokens do NOT auto-refresh and will fail when expired.
    """
    env_map = {
        "context": "DTIAM_CONTEXT",
        "output": "DTIAM_OUTPUT",
        "verbose": "DTIAM_VERBOSE",
        "client_id": "DTIAM_CLIENT_ID",
        "client_secret": "DTIAM_CLIENT_SECRET",
        "account_uuid": "DTIAM_ACCOUNT_UUID",
        "bearer_token": "DTIAM_BEARER_TOKEN",
    }
    env_var = env_map.get(key)
    if env_var:
        return os.environ.get(env_var)
    return None


def mask_secret(value: str, visible_start: int = 4, visible_end: int = 4) -> str:
    """Mask a secret value for display, showing only start and end characters."""
    if len(value) <= visible_start + visible_end:
        return "*" * len(value)
    return value[:visible_start] + "*" * (len(value) - visible_start - visible_end) + value[-visible_end:]
