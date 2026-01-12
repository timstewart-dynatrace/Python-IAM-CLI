# Copilot Instructions for Python-IAM-CLI

## Project Overview

**dtiam** is a kubectl-inspired CLI for managing Dynatrace Identity and Access Management (IAM). It provides a consistent interface for managing users, groups, policies, bindings, boundaries, and environments.

**Key Principle:** Mirror kubectl's command structure and UX patterns while supporting Dynatrace's IAM API specifics.

## Architecture Layers

```
CLI Layer (typer)
    ↓
Commands (commands/*.py) - Individual command implementations
    ↓
Resources (resources/*.py) - CRUD handlers and API abstraction
    ↓
Client & Auth (client.py, utils/auth.py) - HTTP + OAuth2
    ↓
Config (config.py) - Multi-context YAML configuration
```

### Critical Components

1. **Global State (`cli.py`)**: `State` class holds context, output format, verbose/dry-run flags. Access via `from dtiam.cli import state`
2. **Resource Handlers (`resources/base.py`)**: `CRUDHandler[T]` base class providing `list()`, `get()`, `create()`, `delete()` patterns. All handlers inherit this.
3. **Output System (`output.py`)**: `Printer` class and column definitions (`group_columns()`, etc.) handle all output formatting
4. **Configuration (`config.py`)**: Multi-context YAML at `~/.config/dtiam/config` with Pydantic models for type safety
5. **HTTP Client (`client.py`)**: Wrapper around httpx with OAuth2 auto-refresh and retry logic

## Essential Patterns

### Adding a New Command

1. Create `commands/new_feature.py`:
```python
from __future__ import annotations
from typing import Optional
import typer
from dtiam.client import create_client_from_config
from dtiam.config import load_config
from dtiam.output import OutputFormat

app = typer.Typer(no_args_is_help=True)

def get_context() -> str | None:
    from dtiam.cli import state
    return state.context

@app.command()
def do_something(
    name: str = typer.Argument(..., help="Resource name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o"),
) -> None:
    """Command help text."""
    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    try:
        # Implementation
        pass
    finally:
        client.close()
```

2. Register in `cli.py`: `app.add_typer(new_cmd.app, name="new-feature")`

### Adding a Resource Handler

Inherit `CRUDHandler[T]` from `resources/base.py`:

```python
class MyResourceHandler(CRUDHandler[MyModel]):
    @property
    def resource_name(self) -> str:
        return "my-resource"
    
    @property
    def api_path(self) -> str:
        return "/my-resources"
```

Implement custom methods as needed. Always use `self._handle_error()` for API errors.

### Output Patterns

Use `Printer` for consistent formatting:
```python
from dtiam.output import Printer, OutputFormat, group_columns

printer = Printer(format=output or OutputFormat.TABLE, plain=is_plain_mode())
printer.print(data, group_columns())
```

Column definitions live in `output.py` as functions. Format: `[Column("field_name", "HEADER_NAME")]`

## Development Workflow

```bash
# Setup
pip install -e .
pip install -e ".[dev]"

# Run
dtiam --help
dtiam -v get groups  # verbose mode for debugging

# Test
pytest tests/ -v
pytest tests/test_cli.py::test_name -v  # single test

# Lint & Type Check
ruff check src/dtiam --fix
mypy src/dtiam

# Installation (test distribution)
./install.sh  # macOS/Linux
install.bat   # Windows
```

## Key File Locations

| Purpose | File(s) |
|---------|---------|
| Main entry point | `src/dtiam/cli.py` |
| Configuration models | `src/dtiam/config.py` |
| Commands | `src/dtiam/commands/*.py` |
| Resource handlers | `src/dtiam/resources/*.py` |
| Output formatting | `src/dtiam/output.py` |
| HTTP client & OAuth2 | `src/dtiam/client.py`, `src/dtiam/utils/auth.py` |
| Tests | `tests/*.py` |
| Install scripts | `install.sh`, `install.bat` |
| Guides | `CLAUDE.md`, `INSTALLATION.md`, `RELEASES.md` |

## Code Standards

- **Python Version:** 3.10+ (strict type hints required)
- **Type Hints:** All function signatures must have type hints (mypy --strict enforced)
- **Imports:** Use `from __future__ import annotations` in all files
- **Config:** Pydantic BaseModel for data validation
- **CLI:** Typer with type hints for automatic --help generation
- **Output:** Rich library for terminal formatting
- **HTTP:** httpx with context manager (try/finally with `client.close()`)
- **Async:** Use `httpx.AsyncClient` for batch operations

## Authentication & Configuration

**Two methods:**
1. **OAuth2 (recommended):** Auto-refresh, secure for automation. Requires `DTIAM_CLIENT_ID`, `DTIAM_CLIENT_SECRET`
2. **Bearer Token:** Static, fails when expired. Requires `DTIAM_BEARER_TOKEN`

Always include `DTIAM_ACCOUNT_UUID` for both methods.

Config stored at `~/.config/dtiam/config` (XDG compliant). See `config.py` for schema.

## Common Gotchas

- **HTTP Client**: Must call `client.close()` in try/finally or use context manager
- **OAuth2 Tokens**: Auto-refresh happens transparently in `client.py` - don't manually refresh
- **Global State**: Commands access state via `from dtiam.cli import state` - don't pass as function params
- **Resource IDs**: Most APIs use UUID fields, but some accept names. Use `utils/resolver.py` for name→UUID conversion
- **Pagination**: Check `list_key` property (defaults to "items") for API response structure

## Testing

- Tests in `tests/` mirror `src/dtiam/` structure
- Use `pytest` with fixtures from `conftest.py`
- Mock HTTP with `httpx` test client, not actual API calls
- Test commands in isolation with mocked `load_config()` and `create_client_from_config()`

## Distribution

- **Installation Scripts:** `install.sh` (POSIX), `install.bat` (Windows) - test locally before release
- **GitHub Releases:** Use semantic versioning (v3.0.0). See `RELEASES.md` for workflow
- **Installation Methods:** System-wide, user, or virtual environment via scripts

See `INSTALLATION.md` for multi-method installation guide.

## References

- [CLAUDE.md](../CLAUDE.md) - Detailed architecture and API endpoints
- [INSTALLATION.md](../INSTALLATION.md) - User installation guide
- [RELEASES.md](../RELEASES.md) - GitHub Releases workflow
- [docs/COMMANDS.md](../docs/COMMANDS.md) - Command reference
- [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) - Technical deep-dive
