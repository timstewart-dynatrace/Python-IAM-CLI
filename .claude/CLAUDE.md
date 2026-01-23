# CLAUDE.md

> **⚠️ DISCLAIMER**: This tool is provided "as-is" without warranty. **Use at your own risk.**  This tool is an independent, community-driven project and **not produced, endorsed, or supported by Dynatrace**. The authors assume no liability for any issues arising from its use.

This file provides guidance for AI agents working with the dtiam codebase.

## Rules Reference

Detailed guidelines are in separate files:

| File | Description |
|------|-------------|
| [rules/workflow.md](rules/workflow.md) | Development workflow, branching, versioning |
| [rules/code-style.md](rules/code-style.md) | Code style, conventions, patterns |
| [rules/testing.md](rules/testing.md) | Testing standards and practices |
| [rules/security.md](rules/security.md) | Security requirements and best practices |

## Quick Start

```bash
# Install in development mode
pip install -e .

# Run CLI
dtiam --help

# Run tests
pytest tests/ -v

# Type checking
mypy src/dtiam

# Linting
ruff check src/dtiam
```

## Project Overview

**dtiam** is a kubectl-inspired CLI for managing Dynatrace Identity and Access Management (IAM) resources: groups, users, policies, bindings, boundaries, environments, and service users.

**Current Version:** 3.12.0 (in `pyproject.toml` and `src/dtiam/__init__.py`)

## Project Structure

```
src/dtiam/
├── cli.py                   # Entry point, global state, command registration
├── config.py                # Pydantic config models, XDG storage
├── client.py                # httpx HTTP client with OAuth2 and retry
├── output.py                # Output formatters (table/json/yaml/csv)
├── commands/                # CLI command implementations
│   ├── get.py               # List/retrieve resources
│   ├── describe.py          # Detailed resource views
│   ├── create.py            # Create resources
│   ├── delete.py            # Delete resources
│   ├── bulk.py              # Bulk operations
│   └── ...                  # Other command modules
├── resources/               # API resource handlers
│   ├── base.py              # Base handler classes
│   ├── groups.py            # Groups API
│   ├── policies.py          # Policies API
│   ├── bindings.py          # Bindings API
│   └── ...                  # Other resource handlers
└── utils/
    ├── auth.py              # OAuth2 + bearer token management
    ├── resolver.py          # Name-to-UUID resolution
    └── cache.py             # In-memory caching

.claude/
├── CLAUDE.md                # This file - main instructions
└── rules/
    ├── workflow.md          # Development workflow
    ├── code-style.md        # Code style guidelines
    ├── testing.md           # Testing conventions
    └── security.md          # Security requirements
```

## Authentication

**OAuth2 (Recommended)** - Auto-refreshes tokens
```bash
export DTIAM_CLIENT_SECRET=dt0s01.CLIENTID.SECRET
export DTIAM_ACCOUNT_UUID=your-account-uuid
```

**Static Bearer Token** - Does NOT auto-refresh
```bash
export DTIAM_BEARER_TOKEN=your-token
export DTIAM_ACCOUNT_UUID=your-account-uuid
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `DTIAM_CLIENT_SECRET` | OAuth2 client secret |
| `DTIAM_CLIENT_ID` | OAuth2 client ID (optional - auto-extracted) |
| `DTIAM_ACCOUNT_UUID` | Dynatrace account UUID |
| `DTIAM_BEARER_TOKEN` | Static bearer token |
| `DTIAM_API_URL` | Custom IAM API base URL |
| `DTIAM_CONTEXT` | Override current context |

## Key Patterns

### Resource Handler Pattern

All handlers use 404 fallback to list filtering:

```python
def get(self, resource_id: str) -> dict[str, Any]:
    try:
        response = self.client.get(f"{self.api_path}/{resource_id}")
        return response.json()
    except APIError as e:
        if e.status_code == 404:
            items = self.list()
            for item in items:
                if item.get(self.id_field) == resource_id:
                    return item
            return {}
        self._handle_error("get", e)
        return {}
```

### Command Pattern

```python
@app.command("list")
def list_resources(
    name: Optional[str] = typer.Option(None, "--name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o"),
) -> None:
    """List resources."""
    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    try:
        handler = ResourceHandler(client)
        results = handler.list()
        if name:
            results = [r for r in results if name.lower() in r.get("name", "").lower()]
        printer = Printer(format=output or get_output_format())
        printer.print(results, columns())
    finally:
        client.close()
```

### Global State Access

```python
from dtiam.cli import state

state.context    # Optional[str] - context override
state.output     # OutputFormat - output format
state.verbose    # bool - verbose mode
state.dry_run    # bool - dry-run mode
```

## API Endpoints

**IAM API Base:** `https://api.dynatrace.com/iam/v1/accounts/{account_uuid}`

| Resource | Path |
|----------|------|
| Groups | `/groups` |
| Users | `/users` |
| Service Users | `/service-users` |
| Platform Tokens | `/platform-tokens` |
| Policies | `/repo/{level}/{id}/policies` |
| Bindings | `/repo/{level}/{id}/bindings` |
| Boundaries | `/repo/account/{id}/boundaries` |

Level types: `account`, `environment`, `global`

## Development Workflow (Summary)

1. **Create branch:** `git checkout -b feature/my-feature`
2. **Make changes and test:** `pytest tests/ -v`
3. **Update documentation**
4. **Bump version** in `pyproject.toml` and `src/dtiam/__init__.py`
5. **Update CHANGELOG.md**
6. **Commit:** `git commit -m "feat: description"`
7. **Push:** `git push -u origin feature/my-feature`
8. **Merge:** `git checkout main && git merge feature/my-feature --no-ff`

See [rules/workflow.md](rules/workflow.md) for complete workflow details.

## Documentation

| File | Description |
|------|-------------|
| [README.md](../README.md) | Overview and quick start |
| [docs/COMMANDS.md](../docs/COMMANDS.md) | Full command reference |
| [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) | Technical design |
| [docs/QUICK_START.md](../docs/QUICK_START.md) | Getting started guide |
| [examples/](../examples/) | Sample configurations |

## Troubleshooting

**"No context configured"**
```bash
dtiam config set-credentials NAME --client-secret dt0s01.XXX.YYY --account-uuid UUID
dtiam config use-context NAME
```

**"Permission denied"** - OAuth2 client needs scopes: `account-idm-read`, `iam-policies-management`

**Import errors** - Install in dev mode: `pip install -e .`
