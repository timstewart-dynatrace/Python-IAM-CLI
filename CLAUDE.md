# CLAUDE.md

This file provides guidance for AI agents working with the dtiam codebase.

> **DISCLAIMER:** This tool is provided "as-is" without warranty. Use at your own risk. This is an independent, community-developed tool and is **NOT produced, endorsed, or supported by Dynatrace**.

## Documentation Structure

Project instructions are organized in the `.claude/` directory:

```
.claude/
├── CLAUDE.md                # Condensed reference (alternative entry point)
└── rules/
    ├── workflow.md          # Development workflow, branching, versioning
    ├── code-style.md        # Code style guidelines and conventions
    ├── testing.md           # Testing standards and practices
    └── security.md          # Security requirements and best practices
```

**For detailed guidelines, see the individual rule files in [.claude/rules/](.claude/rules/).**

---

## Development Workflow Summary

> **Full details:** [.claude/rules/workflow.md](.claude/rules/workflow.md)

### MANDATORY Requirements

1. **NEVER commit directly to main** - Use feature branches (`feature/name` or `fix/name`)
2. **Update documentation BEFORE merge** - CLAUDE.md, docs/COMMANDS.md, README.md
3. **Bump version** in `pyproject.toml` and `src/dtiam/__init__.py`
4. **Update CHANGELOG.md**
5. **Merge with:** `git merge feature/name --no-ff`

### Quick Workflow

```bash
git checkout -b feature/my-feature
# ... make changes ...
pytest tests/ -v
# ... update docs, bump version ...
git add . && git commit -m "feat: description"
git push -u origin feature/my-feature
git checkout main && git merge feature/my-feature --no-ff && git push
```

### Version Management

**Current version:** 3.12.0

| Change Type | Bump | Example |
|-------------|------|---------|
| Breaking | MAJOR | 3.0.0 → 4.0.0 |
| Feature | MINOR | 3.0.0 → 3.1.0 |
| Bug fix | PATCH | 3.0.0 → 3.0.1 |

---

## Project Overview

**dtiam** is a kubectl-inspired CLI for managing Dynatrace Identity and Access Management (IAM) resources: groups, users, policies, bindings, boundaries, environments, and service users.

### Quick Reference

```bash
# Install in development mode
pip install -e .

# Run CLI
dtiam --help

# Run tests
pytest tests/ -v

# Type checking & linting
mypy src/dtiam
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
```

---

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
| `DTIAM_CLIENT_ID` | OAuth2 client ID (optional - auto-extracted from secret) |
| `DTIAM_ACCOUNT_UUID` | Dynatrace account UUID |
| `DTIAM_BEARER_TOKEN` | Static bearer token |
| `DTIAM_API_URL` | Custom IAM API base URL |
| `DTIAM_CONTEXT` | Override current context |
| `DTIAM_ENVIRONMENT_URL` | Environment URL for App Engine Registry |

### Credential Storage

Credentials stored in config can include:

| Field | Description |
|-------|-------------|
| `client-id` | OAuth2 client ID |
| `client-secret` | OAuth2 client secret |
| `environment-url` | Dynatrace environment URL |
| `api-url` | Custom IAM API base URL (stored per-credential) |
| `scopes` | Custom OAuth2 scopes (space-separated) |

---

## Key Patterns

> **Full code style guide:** [.claude/rules/code-style.md](.claude/rules/code-style.md)

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

---

## API Endpoints

**IAM API Base:** `https://api.dynatrace.com/iam/v1/accounts/{account_uuid}`

| Resource | Path |
|----------|------|
| Groups | `/groups` |
| Users | `/users` |
| Service Users | `/service-users` |
| Platform Tokens | `/platform-tokens` |
| Limits | `/limits` |
| Environments | `/environments` |
| Policies | `/repo/{level}/{id}/policies` |
| Bindings | `/repo/{level}/{id}/bindings` |
| Boundaries | `/repo/account/{id}/boundaries` |

**Level types:** `account`, `environment`, `global`

**App Engine Registry API:** `https://{env-id}.apps.dynatrace.com/platform/app-engine/registry/v1`

| Resource | Path |
|----------|------|
| Apps | `/apps` |

---

## Filtering Resources

All `get` commands support partial text matching:

| Command | Filter | Description |
|---------|--------|-------------|
| `get groups` | `--name` | Filter by group name |
| `get users` | `--email` | Filter by email |
| `get policies` | `--name` | Filter by policy name |
| `get boundaries` | `--name` | Filter by boundary name |
| `get environments` | `--name` | Filter by environment name |
| `get service-users` | `--name` | Filter by service user name |

**Behavior:** Case-insensitive substring match, applied client-side after fetching list.

---

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
      environment-url: https://abc123.live.dynatrace.com
      api-url: https://api.dynatrace.com/iam/v1
      scopes: account-idm-read iam:users:read
```

---

## Testing

> **Full testing guide:** [.claude/rules/testing.md](.claude/rules/testing.md)

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src/dtiam

# Type checking
mypy src/dtiam --strict

# Linting with fix
ruff check src/dtiam --fix
```

---

## Security

> **Full security guide:** [.claude/rules/security.md](.claude/rules/security.md)

Key requirements:
- Never log full secrets (use `mask_secret()`)
- Validate user input before API calls
- Require confirmation for destructive operations
- Support dry-run mode for bulk operations

---

## Troubleshooting

**"No context configured"**
```bash
dtiam config set-credentials NAME --client-secret dt0s01.XXX.YYY --account-uuid UUID
dtiam config use-context NAME
```

**"Permission denied"** - OAuth2 client needs scopes: `account-idm-read`, `iam-policies-management`

**Import errors** - Install in dev mode: `pip install -e .`

---

## Documentation

| File | Description |
|------|-------------|
| [README.md](README.md) | Overview and quick start |
| [docs/COMMANDS.md](docs/COMMANDS.md) | Full command reference |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Technical design |
| [docs/QUICK_START.md](docs/QUICK_START.md) | Getting started guide |
| [examples/](examples/) | Sample configurations |
| [INSTALLATION.md](INSTALLATION.md) | Installation guide |
| [RELEASES.md](RELEASES.md) | Release workflow |
