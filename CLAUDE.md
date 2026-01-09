# CLAUDE.md

This file provides guidance for AI agents working with the dtiam codebase.

> **DISCLAIMER:** This tool is provided "as-is" without warranty. Use at your own risk. This is an independent, community-developed tool and is **NOT produced, endorsed, or supported by Dynatrace**.

## Project Overview

**dtiam** is a kubectl-inspired CLI for managing Dynatrace Identity and Access Management (IAM) resources. It provides a consistent interface for managing groups, users, policies, bindings, boundaries, environments, and management zones.

> **Note:** Management Zone features are legacy-only and will be removed in a future release.

## Quick Reference

### Build & Run

```bash
# Install in development mode
pip install -e .

# Run CLI
dtiam --help

# Run with verbose output
dtiam -v get groups

# Run tests
pytest tests/ -v

# Run type checking
mypy src/dtiam

# Run linting
ruff check src/dtiam
```

### Project Structure

```
src/dtiam/
├── cli.py                   # Entry point, global state, command registration
├── config.py                # Pydantic config models, XDG storage
├── client.py                # httpx HTTP client with OAuth2 and retry
├── output.py                # Output formatters (table/json/yaml/csv)
├── commands/                # CLI command implementations
│   ├── config.py            # Config management commands
│   ├── get.py               # List/retrieve resources
│   ├── describe.py          # Detailed resource views
│   ├── create.py            # Create resources
│   ├── delete.py            # Delete resources
│   ├── user.py              # User management
│   ├── service_user.py      # Service user (OAuth client) management
│   ├── account.py           # Account limits and subscriptions
│   ├── bulk.py              # Bulk operations
│   ├── template.py          # Template system
│   ├── zones.py             # Management zones (legacy - will be removed)
│   ├── analyze.py           # Permissions analysis
│   ├── export.py            # Export operations
│   ├── group.py             # Advanced group ops
│   ├── boundary.py          # Boundary attach/detach
│   └── cache.py             # Cache management
├── resources/               # API resource handlers
│   ├── base.py              # Base handler classes
│   ├── groups.py            # Groups API
│   ├── policies.py          # Policies API
│   ├── users.py             # Users API
│   ├── bindings.py          # Bindings API
│   ├── boundaries.py        # Boundaries API
│   ├── environments.py      # Environments API
│   ├── zones.py             # Management zones API (legacy - will be removed)
│   ├── service_users.py     # Service users (OAuth clients) API
│   ├── limits.py            # Account limits API
│   └── subscriptions.py     # Subscriptions API
└── utils/
    ├── auth.py              # OAuth2 + bearer token management
    ├── resolver.py          # Name-to-UUID resolution
    ├── templates.py         # Template rendering
    ├── permissions.py       # Permissions calculation
    └── cache.py             # In-memory caching
```

## Authentication

dtiam supports two authentication methods:

### OAuth2 (Recommended)
- Auto-refreshes tokens when expired
- Best for automation, CI/CD, long-running processes
- Requires `DTIAM_CLIENT_ID`, `DTIAM_CLIENT_SECRET`, `DTIAM_ACCOUNT_UUID`

### Bearer Token (Static)
- Does NOT auto-refresh (fails when token expires)
- Best for quick testing, debugging, one-off operations
- Requires `DTIAM_BEARER_TOKEN`, `DTIAM_ACCOUNT_UUID`

### Environment Variables

| Variable | Description |
|----------|-------------|
| `DTIAM_BEARER_TOKEN` | Static bearer token (alternative to OAuth2) |
| `DTIAM_CLIENT_ID` | OAuth2 client ID |
| `DTIAM_CLIENT_SECRET` | OAuth2 client secret |
| `DTIAM_ACCOUNT_UUID` | Dynatrace account UUID |
| `DTIAM_CONTEXT` | Override current context |

## Key Patterns

### Adding a New Command

1. Create command file in `commands/`:
```python
"""New feature commands."""
from __future__ import annotations

import typer
from rich.console import Console

from dtiam.client import create_client_from_config
from dtiam.config import load_config
from dtiam.output import OutputFormat, Printer

app = typer.Typer(no_args_is_help=True)
console = Console()

def get_context() -> str | None:
    from dtiam.cli import state
    return state.context

def is_verbose() -> bool:
    from dtiam.cli import state
    return state.verbose

@app.command("do-something")
def do_something(
    name: str = typer.Argument(..., help="Resource name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Do something useful."""
    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    try:
        # Implementation here
        pass
    finally:
        client.close()
```

2. Register in `cli.py`:
```python
from dtiam.commands import new_feature as new_cmd
app.add_typer(new_cmd.app, name="new-feature", help="New feature operations")
```

### Adding a New Resource Handler

1. Create handler in `resources/`:
```python
"""New resource handler."""
from __future__ import annotations
from typing import Any
from dtiam.resources.base import CRUDHandler

class NewResourceHandler(CRUDHandler[Any]):
    @property
    def resource_name(self) -> str:
        return "new-resource"

    @property
    def api_path(self) -> str:
        return "/new-resources"

    @property
    def list_key(self) -> str:
        return "items"  # Key in API response containing the list
```

2. Add columns in `output.py`:
```python
def new_resource_columns() -> list[Column]:
    return [
        Column("uuid", "UUID"),
        Column("name", "NAME"),
        Column("description", "DESCRIPTION"),
    ]
```

### Global State Access

Commands access global CLI state through imports:
```python
from dtiam.cli import state

# Available properties:
state.context    # Optional[str] - context override
state.output     # OutputFormat - output format
state.verbose    # bool - verbose mode
state.plain      # bool - plain mode (no colors)
state.dry_run    # bool - dry-run mode
```

### HTTP Client Usage

Always use context manager or try/finally:
```python
config = load_config()
client = create_client_from_config(config, get_context(), is_verbose())

try:
    response = client.get("/groups")
    data = response.json()
finally:
    client.close()
```

### Output Formatting

Use the Printer class for consistent output:
```python
from dtiam.output import Printer, OutputFormat, group_columns

printer = Printer(format=output or get_output_format(), plain=is_plain_mode())
printer.print(data, group_columns())
```

## API Endpoints

Base URL: `https://api.dynatrace.com/iam/v1/accounts/{account_uuid}`

| Resource | Path |
|----------|------|
| Groups | `/groups` |
| Users | `/users` |
| Service Users | `/service-users` |
| Limits | `/limits` |
| Environments | `/environments` |
| Policies | `/repo/{level_type}/{level_id}/policies` |
| Bindings | `/repo/{level_type}/{level_id}/bindings` |
| Boundaries | `/repo/{level_type}/{level_id}/boundaries` |

**Resolution API** (for effective permissions):
Base URL: `https://api.dynatrace.com/iam/v1`

| Resource | Path |
|----------|------|
| Effective Permissions | `/resolution/{level_type}/{level_id}/effectivepermissions` |

**Subscription API**:
Base URL: `https://api.dynatrace.com/sub/v2/accounts/{account_uuid}`

| Resource | Path |
|----------|------|
| Subscriptions | `/subscriptions` |
| Forecast | `/subscriptions/forecast` |

Query parameters for effective permissions:
- `entityId` - User UID or Group UUID
- `entityType` - "user" or "group"
- `page` - Page number (default: 1)
- `size` - Page size (default: 100)
- `services` - Comma-separated service filter

Level types: `account`, `environment`, `global`

## API Coverage & Missing Operations

**Implemented (newly added):**
| Endpoint | Operation | Handler Method |
|----------|-----------|----------------|
| `PUT /users/{email}/groups` | Replace user's groups | `UserHandler.replace_groups()` |
| `DELETE /users/{email}/groups` | Remove from groups | `UserHandler.remove_from_groups()` |
| `POST /users/{email}` | Add to multiple groups | `UserHandler.add_to_groups()` |
| `GET /policies/aggregate` | List all policies | `PolicyHandler.list_aggregate()` |
| `POST /policies/validation` | Validate policy | `PolicyHandler.validate()` |
| `POST /policies/validation/{id}` | Validate update | `PolicyHandler.validate_update()` |
| `GET /bindings/{policyUuid}` | Get policy bindings | `BindingHandler.get_for_policy()` |
| `GET /bindings/{policyUuid}/{groupUuid}` | Get specific binding | `BindingHandler.get_policy_group_binding()` |
| `GET /bindings/descendants/{policyUuid}` | Descendant bindings | `BindingHandler.get_descendants()` |
| `PUT /bindings/groups/{groupUuid}` | Update group bindings | `BindingHandler.update_group_bindings()` |

**Not yet implemented:**
| Endpoint | Operation | Notes |
|----------|-----------|-------|
| `DELETE /bindings` | Delete all bindings | Level-wide deletion (dangerous) |
| **Platform Tokens** | | Entire resource |
| `GET /platform-tokens` | List tokens | `platform-token:tokens:manage` |
| `POST /platform-tokens` | Generate token | `platform-token:tokens:manage` |
| `DELETE /platform-tokens/{id}` | Delete token | `platform-token:tokens:manage` |
| **Environment IP Allowlist** | | |
| `GET /environments/{id}/ip-allowlist` | Get allowlist | Bearer token |
| `PUT /environments/{id}/ip-allowlist` | Set allowlist | Bearer token |
| **Subscription Details** | | |
| `GET /subscriptions/{id}/cost` | Get costs | Bearer token |
| `GET /subscriptions/{id}/environments/usage` | Env usage | v3 API |

## Configuration

Config file: `~/.config/dtiam/config` (YAML)

```yaml
api-version: v1
kind: Config
current-context: production
contexts:
  - name: production
    context:
      account-uuid: abc-123
      credentials-ref: prod-creds
credentials:
  - name: prod-creds
    credential:
      client-id: dt0s01.XXX
      client-secret: dt0s01.XXX.YYY
```

Environment variable overrides:
- `DTIAM_CONTEXT` - context name
- `DTIAM_OUTPUT` - output format
- `DTIAM_VERBOSE` - verbose mode
- `DTIAM_CLIENT_ID` - OAuth2 client ID
- `DTIAM_CLIENT_SECRET` - OAuth2 client secret
- `DTIAM_ACCOUNT_UUID` - account UUID

## Common Tasks

### Fix Type Errors

```bash
mypy src/dtiam --strict
```

Common fixes:
- Add return type annotations
- Use `from __future__ import annotations` for forward references
- Use `Optional[T]` for nullable types

### Fix Lint Errors

```bash
ruff check src/dtiam --fix
```

### Test a Command

```bash
# Install first
pip install -e .

# Test command
dtiam --help
dtiam get groups --help
dtiam -v get groups  # verbose mode
```

### Debug Authentication

```bash
# Verbose mode shows token requests
dtiam -v get groups
```

Check `~/.config/dtiam/config` for credential configuration.

## Code Style

- Use `from __future__ import annotations` in all files
- Type hints required for all function signatures
- Use Pydantic models for data validation
- Rich library for terminal output
- Typer for CLI with type hints
- httpx for HTTP requests

## Dependencies

```
typer[all]>=0.9.0      # CLI framework
httpx>=0.27.0          # HTTP client
pydantic>=2.0          # Data validation
pyyaml>=6.0            # YAML parsing
rich>=13.0             # Terminal formatting
platformdirs>=4.0      # XDG directories
```

## Troubleshooting

### "No context configured"

Run:
```bash
dtiam config set-credentials NAME --client-id XXX --client-secret YYY
dtiam config set-context NAME --account-uuid UUID --credentials-ref NAME
dtiam config use-context NAME
```

### "Permission denied"

OAuth2 client needs appropriate scopes:
- `account-idm-read` / `account-idm-write`
- `iam-policies-management`
- `account-env-read`
- `iam:effective-permissions:read` (for effective permissions API)

### Import Errors

Ensure installed in development mode:
```bash
pip install -e .
```

## Documentation

- [README.md](README.md) - Overview and quick start
- [docs/QUICK_START.md](docs/QUICK_START.md) - Detailed getting started
- [docs/COMMANDS.md](docs/COMMANDS.md) - Full command reference
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Technical design
- [docs/API_REFERENCE.md](docs/API_REFERENCE.md) - Programmatic usage
