# CLAUDE.md

This file provides guidance for AI agents working with the dtiam codebase.

> **DISCLAIMER:** This tool is provided "as-is" without warranty. Use at your own risk. This is an independent, community-developed tool and is **NOT produced, endorsed, or supported by Dynatrace**.

## Development Workflow - MANDATORY

**ALL development work MUST follow this workflow:**

### Branching Requirements

1. **NEVER commit features directly to main**
   - ALL new features, enhancements, and non-trivial changes MUST be developed in a feature branch
   - Branch naming convention: `feature/descriptive-name` or `fix/descriptive-name`
   - Only documentation fixes and critical hotfixes may be committed directly to main (with approval)

2. **Feature Branch Workflow**
   ```bash
   # Create feature branch from main
   git checkout main
   git pull
   git checkout -b feature/my-feature

   # Develop and commit
   git add <files>
   git commit -m "feat: description"

   # Push feature branch
   git push -u origin feature/my-feature
   ```

3. **Documentation Requirements - MANDATORY**
   - **ALL features MUST be documented BEFORE merging to main**
   - Documentation checklist (ALL must be completed):
     - [ ] [CLAUDE.md](CLAUDE.md) - Add to project structure, patterns, or API endpoints
     - [ ] [docs/COMMANDS.md](docs/COMMANDS.md) - Full command reference with examples
     - [ ] [README.md](README.md) - Update quick start or features section
     - [ ] [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Update if architecture changes
     - [ ] [examples/](examples/) - Add sample files if applicable
     - [ ] Code comments and docstrings for new functions/classes

4. **Merge Process**
   ```bash
   # Before merging: verify ALL documentation is complete
   git checkout main
   git merge feature/my-feature --no-ff

   # If documentation is missing, DO NOT MERGE
   # Create documentation commits in the feature branch first
   ```

5. **Verification Before Merge**
   - Run tests: `pytest tests/ -v`
   - Verify command help: `dtiam <new-command> --help`
   - Check all documentation files are updated
   - Ensure examples are provided
   - Verify CLAUDE.md includes new patterns/endpoints

### Why This Matters

- **Prevents incomplete features in main**: Feature branches isolate work-in-progress
- **Ensures documentation completeness**: No undocumented features reach users
- **Enables easy rollback**: Feature branches can be deleted if not needed
- **Maintains clean history**: Main branch only contains complete, documented features
- **Facilitates collaboration**: Multiple features can be developed in parallel

### Example: Adding a New Resource

```bash
# 1. Create feature branch
git checkout -b feature/add-apps-resource

# 2. Implement feature
# - Add src/dtiam/resources/apps.py
# - Add command in src/dtiam/commands/get.py
# - Add output columns in src/dtiam/output.py

# 3. Test implementation
pip install -e .
dtiam get apps --help

# 4. Document EVERYTHING
# - Update CLAUDE.md (project structure)
# - Update docs/COMMANDS.md (command reference)
# - Update README.md (add to resources table)
# - Update docs/ARCHITECTURE.md (add to resource handlers)
# - Add examples/apps/ directory with samples

# 5. Commit feature and documentation together
git add .
git commit -m "feat: add apps resource for App Engine Registry

- Add AppHandler for App Engine Registry API
- Add get apps command with --environment option
- Add app_columns() for table output
- Document in CLAUDE.md, COMMANDS.md, README.md, ARCHITECTURE.md
- Add usage examples"

# 6. Push feature branch
git push -u origin feature/add-apps-resource

# 7. Merge to main (only after ALL documentation complete)
git checkout main
git merge feature/add-apps-resource --no-ff
git push
```

**REMEMBER: Documentation is NOT optional. It is MANDATORY before merge.**

### Version Management - MANDATORY

**ALL merges to main that add features or fixes MUST increment the version number.**

Current version: **3.1.0** (defined in `pyproject.toml` and `src/dtiam/__init__.py`)

#### Semantic Versioning (SemVer)

We follow [Semantic Versioning 2.0.0](https://semver.org/):

**Format:** `MAJOR.MINOR.PATCH` (e.g., 3.0.0)

1. **MAJOR version** (X.0.0) - Incompatible API changes
   - Breaking changes to CLI commands
   - Removal of commands or options
   - Changes that break existing scripts/workflows
   - Example: Removing `--zone` flag, changing command structure

2. **MINOR version** (3.X.0) - New features (backwards-compatible)
   - New commands (e.g., `get apps`)
   - New options to existing commands
   - New resource handlers
   - Example: Adding `bulk create-groups-with-policies`

3. **PATCH version** (3.0.X) - Bug fixes (backwards-compatible)
   - Bug fixes
   - Documentation updates
   - Performance improvements
   - Example: Fixing error handling, updating help text

#### When to Increment

**Before merging to main:**

```bash
# For new features (MINOR)
# 3.0.0 -> 3.1.0
git checkout feature/my-feature
# Edit pyproject.toml: version = "3.1.0"
# Edit src/dtiam/__init__.py: __version__ = "3.1.0"
git add pyproject.toml src/dtiam/__init__.py
git commit -m "chore: bump version to 3.1.0"

# For bug fixes (PATCH)
# 3.0.0 -> 3.0.1
git checkout fix/my-bugfix
# Edit pyproject.toml: version = "3.0.1"
# Edit src/dtiam/__init__.py: __version__ = "3.0.1"
git add pyproject.toml src/dtiam/__init__.py
git commit -m "chore: bump version to 3.0.1"

# Then merge to main
git checkout main
git merge feature/my-feature --no-ff
```

#### Version Bump Checklist

Before merging to main, ensure:
- [ ] Version incremented in `pyproject.toml` (line 7)
- [ ] Version incremented in `src/dtiam/__init__.py` (line 3)
- [ ] Both files have **matching** version numbers
- [ ] Correct increment type (MAJOR/MINOR/PATCH)
- [ ] Version bump committed in feature branch before merge

#### Version Display

Users can check the version:
```bash
dtiam --version
# Output: dtiam version 3.0.0
```

#### Examples

**Adding new feature (`get apps` command):**
- Type: MINOR version bump
- Before: 3.0.0
- After: 3.1.0
- Commit: `chore: bump version to 3.1.0`

**Adding bulk command:**
- Type: MINOR version bump
- Before: 3.1.0
- After: 3.2.0
- Commit: `chore: bump version to 3.2.0`

**Fixing bug in error handling:**
- Type: PATCH version bump
- Before: 3.2.0
- After: 3.2.1
- Commit: `chore: bump version to 3.2.1`

**Documentation-only changes:**
- Type: PATCH version bump (optional)
- Before: 3.2.1
- After: 3.2.2
- Note: Documentation fixes may optionally bump PATCH

**REMEMBER: Version increments are MANDATORY for all feature and fix merges to main.**

### CHANGELOG Management - MANDATORY

**ALL changes MUST be documented in CHANGELOG.md**

We follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

#### CHANGELOG Structure

```markdown
## [Unreleased]

### Added
- New features go here

### Changed
- Changes to existing functionality

### Deprecated
- Features marked for removal

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security fixes

## [3.1.0] - 2025-01-13

### Added
- Actual released features
...
```

#### When to Update CHANGELOG

**In your feature branch, BEFORE merging:**

1. **For new features** - Add to `## [Unreleased]` → `### Added` section
2. **For changes** - Add to `## [Unreleased]` → `### Changed` section
3. **For bug fixes** - Add to `## [Unreleased]` → `### Fixed` section
4. **For documentation** - Add to `## [Unreleased]` → `### Documentation` section (optional)

#### Workflow Example

```bash
# In feature branch
git checkout feature/add-apps

# 1. Implement feature
# 2. Update CHANGELOG.md
# Add to [Unreleased] section:
### Added
- `get apps` command for listing Dynatrace Apps from App Engine Registry
  - Supports --environment flag or DTIAM_ENVIRONMENT_URL
  - --ids flag for policy statements

# 3. Bump version
# Edit pyproject.toml: version = "3.1.0"
# Edit src/dtiam/__init__.py: __version__ = "3.1.0"

# 4. Move [Unreleased] to version section
# Change:
## [Unreleased]
### Added
- Feature

# To:
## [Unreleased]
(empty)

## [3.1.0] - 2025-01-13
### Added
- Feature

# 5. Update comparison links at bottom
[Unreleased]: .../compare/v3.1.0...HEAD
[3.1.0]: .../compare/v3.0.0...v3.1.0

# 6. Commit
git add CHANGELOG.md pyproject.toml src/dtiam/__init__.py
git commit -m "chore: bump version to 3.1.0 and update CHANGELOG"

# 7. Merge to main
git checkout main
git merge feature/add-apps --no-ff
```

#### CHANGELOG Checklist

Before merging to main:
- [ ] CHANGELOG.md updated with your changes
- [ ] Changes in appropriate section (Added/Changed/Fixed/etc)
- [ ] [Unreleased] section moved to version section
- [ ] Version number matches pyproject.toml and __init__.py
- [ ] Comparison links updated at bottom
- [ ] Date added to version heading (YYYY-MM-DD)

### Creating GitHub Releases

**After merging to main with version bump:**

```bash
# 1. Create git tag
git tag -a v3.1.0 -m "Release version 3.1.0"
git push origin v3.1.0

# 2. Create GitHub Release (web UI or CLI)
gh release create v3.1.0 \
  --title "v3.1.0" \
  --notes-file <(sed -n '/## \[3.1.0\]/,/## \[3.0.0\]/p' CHANGELOG.md | head -n -1)

# Or use web interface:
# https://github.com/timstewart-dynatrace/Python-IAM-CLI/releases/new
```

See [RELEASES.md](RELEASES.md) for detailed release instructions.

**REMEMBER: CHANGELOG updates are MANDATORY for all merges to main.**

## Project Overview

**dtiam** is a kubectl-inspired CLI for managing Dynatrace Identity and Access Management (IAM) resources. It provides a consistent interface for managing groups, users, policies, bindings, boundaries, environments, and management zones.

> **Note:** Management Zone features are legacy-only and will be removed in a future release.

## Quick Reference

### Build & Run

```bash
# Install in development mode (from source)
pip install -e .

# Or use automated installation script
./install.sh           # macOS/Linux
install.bat           # Windows

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
│   ├── subscriptions.py     # Subscriptions API
│   └── apps.py              # App Engine Registry API
└── utils/
    ├── auth.py              # OAuth2 + bearer token management
    ├── resolver.py          # Name-to-UUID resolution
    ├── templates.py         # Template rendering
    ├── permissions.py       # Permissions calculation
    └── cache.py             # In-memory caching

examples/                    # Example configurations and scripts
├── README.md                # Examples documentation
├── auth/                    # Authentication examples
│   └── .env.example         # Environment variable template
├── boundaries/              # Policy boundary examples
│   ├── production-only.yaml # Restrict to production zones
│   └── team-scoped.yaml     # Team-specific zone restrictions
├── bulk/                    # Bulk operation sample files
│   ├── sample_users.csv            # For bulk add-users-to-group
│   ├── sample_groups.yaml          # For bulk create-groups
│   ├── sample_bindings.yaml        # For bulk create-bindings
│   └── sample_bulk_groups.csv      # For bulk create-groups-with-policies
├── config/                  # Configuration examples
│   └── multi-account.yaml   # Multi-account config template
├── groups/                  # Group configuration examples
│   ├── team-group.yaml      # Standard team group
│   ├── admin-group.yaml     # Administrator group
│   └── readonly-group.yaml  # Read-only access group
├── policies/                # Policy examples
│   ├── README.md            # Policy documentation
│   ├── viewer-policy.yaml   # Read-only policy
│   ├── devops-policy.yaml   # DevOps permissions
│   ├── slo-manager.yaml     # SLO management
│   ├── settings-writer.yaml # Settings write access
│   └── alerting-only.yaml   # Schema-restricted policy
├── service-users/           # Service user (OAuth client) examples
│   ├── ci-pipeline.yaml     # CI/CD automation service user
│   └── monitoring-bot.yaml  # Read-only monitoring service user
├── templates/               # Reusable templates
│   ├── group-team.yaml      # Team group template
│   ├── policy-readonly.yaml # Read-only policy template
│   └── boundary-zone.yaml   # Zone boundary template
└── scripts/                 # Shell script examples
    ├── example_cli_lifecycle.sh      # Full IAM lifecycle validation
    └── example_common_workflows.sh   # Common workflow reference
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
| `DTIAM_ENVIRONMENT_URL` | Environment URL for App Engine Registry (e.g., abc12345.apps.dynatrace.com) |

## Key Patterns

### Bulk Operations

**Integrated Bulk Creation:**

The `bulk create-groups-with-policies` command creates groups, boundaries, and bindings in one operation:

```bash
# Preview changes (dry-run by default)
dtiam bulk create-groups-with-policies --file examples/bulk/sample_bulk_groups.csv

# Execute for real
dtiam bulk create-groups-with-policies --file examples/bulk/sample_bulk_groups.csv --no-dry-run
```

CSV format:
```csv
group_name,policy_name,level,level_id,management_zones,boundary_name,description
LOB5-TEST,Standard User,account,,,,LOB5 global read
LOB5-TEST,Pro User,environment,yhu28601,LOB5,LOB5-Boundary,LOB5 restricted write
```

**Features:**
- Creates groups if they don't exist
- Creates boundaries with correct Dynatrace query format
- Creates policy bindings at account or environment level
- Supports dry-run mode (enabled by default)
- Shows progress and summary

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

### Boundary Query Format

Boundaries use the following Dynatrace-compliant format:

```python
# Single zone
environment:management-zone IN ("Production");
storage:dt.security_context IN ("Production");
settings:dt.security_context IN ("Production")

# Multiple zones
environment:management-zone IN ("Production", "Staging");
storage:dt.security_context IN ("Production", "Staging");
settings:dt.security_context IN ("Production", "Staging")
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

**App Engine Registry API**:
Base URL: `https://{environment-id}.apps.dynatrace.com/platform/app-engine/registry/v1`

| Resource | Path |
|----------|------|
| Apps | `/apps` |
| App Details | `/apps/{id}` |

Note: App IDs can be used in policy/boundary statements like `shared:app-id = '{app.id}';`

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

## Distribution & Installation

**For End Users:**
- [INSTALLATION.md](INSTALLATION.md) - Installation guide with multiple methods
- [RELEASES.md](RELEASES.md) - How to distribute via GitHub Releases
- Automated scripts: `install.sh` (macOS/Linux), `install.bat` (Windows)

**For Developers:**
- Use `./install.sh` or `install.bat` to test user installation flow
- Scripts support system-wide, user, and virtual environment installations
- Always test distribution before creating a GitHub Release

## Documentation

- [README.md](README.md) - Overview and quick start
- [docs/QUICK_START.md](docs/QUICK_START.md) - Detailed getting started
- [docs/COMMANDS.md](docs/COMMANDS.md) - Full command reference
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Technical design
- [docs/API_REFERENCE.md](docs/API_REFERENCE.md) - Programmatic usage
- [examples/README.md](examples/README.md) - Sample configurations and scripts
- [INSTALLATION.md](INSTALLATION.md) - Installation guide for end users
- [RELEASES.md](RELEASES.md) - GitHub Releases workflow guide
