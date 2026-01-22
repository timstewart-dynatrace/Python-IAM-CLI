# Code Style Guidelines

This document defines the code style and conventions for the dtiam project.

## Python Style

### Imports

- Use `from __future__ import annotations` at the top of all files
- Group imports in order: standard library, third-party, local
- Sort imports alphabetically within each group

```python
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
import typer
from pydantic import BaseModel

from dtiam.client import Client, create_client_from_config
from dtiam.config import load_config
```

### Type Hints

- Type hints are **required** for all function signatures
- Use `Optional[T]` for nullable types
- Use `list[T]` and `dict[K, V]` (lowercase) for Python 3.9+ style

```python
def get_user(user_id: str, include_groups: bool = False) -> dict[str, Any]:
    """Get user by ID."""
    ...

def find_users(email: str | None = None) -> list[dict[str, Any]]:
    """Find users, optionally filtering by email."""
    ...
```

### Docstrings

- Use Google-style docstrings for all public functions and classes
- Include Args, Returns, and Raises sections as appropriate

```python
def create_group(name: str, description: str | None = None) -> dict[str, Any]:
    """Create a new IAM group.

    Args:
        name: Group name (required)
        description: Optional group description

    Returns:
        Created group dictionary with uuid and metadata

    Raises:
        ValueError: If name is empty
        APIError: If API request fails
    """
```

### Error Handling

- Use specific exception types, not bare `except:`
- Re-raise with context using `from e`
- Handle API errors gracefully with fallback behavior where appropriate

```python
try:
    response = self.client.get(f"{self.api_path}/{resource_id}")
    return response.json()
except APIError as e:
    if e.status_code == 404:
        # Fall back to filtering the list
        items = self.list()
        for item in items:
            if item.get("uuid") == resource_id:
                return item
        return {}
    self._handle_error("get", e)
    return {}
```

## Project Conventions

### File Organization

- One class per file for resource handlers
- Group related commands in single files
- Keep utility functions in `utils/` directory

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Files | lowercase_snake | `service_users.py` |
| Classes | PascalCase | `ServiceUserHandler` |
| Functions | lowercase_snake | `get_by_name()` |
| Constants | UPPERCASE_SNAKE | `DEFAULT_IAM_API_BASE` |
| Type aliases | PascalCase | `LevelType` |

### Resource Handlers

All resource handlers should:

1. Inherit from `ResourceHandler` or `CRUDHandler`
2. Define `resource_name`, `api_path`, and `id_field` properties
3. Implement `get()` with 404 fallback to list filtering
4. Provide `get_by_name()` for name-based lookups

```python
class NewResourceHandler(ResourceHandler[Any]):
    @property
    def resource_name(self) -> str:
        return "new-resource"

    @property
    def api_path(self) -> str:
        return "/new-resources"

    @property
    def id_field(self) -> str:
        return "uuid"

    def get(self, resource_id: str) -> dict[str, Any]:
        """Get resource with 404 fallback to list."""
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

### CLI Commands

Commands should:

1. Use Typer for CLI definition
2. Access global state through `dtiam.cli.state`
3. Always close the client in a `finally` block
4. Use the `Printer` class for output

```python
@app.command("list")
def list_resources(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List all resources."""
    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    try:
        handler = ResourceHandler(client)
        results = handler.list()

        if name:
            results = [r for r in results if name.lower() in r.get("name", "").lower()]

        printer = Printer(format=output or get_output_format(), plain=is_plain_mode())
        printer.print(results, resource_columns())
    finally:
        client.close()
```

## Dependencies

Required packages:

```
typer[all]>=0.9.0      # CLI framework
httpx>=0.27.0          # HTTP client
pydantic>=2.0          # Data validation
pyyaml>=6.0            # YAML parsing
rich>=13.0             # Terminal formatting
platformdirs>=4.0      # XDG directories
```

## Linting & Type Checking

Run before committing:

```bash
# Type checking
mypy src/dtiam --strict

# Linting with auto-fix
ruff check src/dtiam --fix

# Format code
ruff format src/dtiam
```
