# dtiam - Dynatrace IAM CLI

A kubectl-inspired command-line interface for managing Dynatrace Identity and Access Management resources.

## Features

- **kubectl-style commands** - Familiar syntax: `get`, `describe`, `create`, `delete`, `apply`
- **Multi-context configuration** - Manage multiple Dynatrace accounts with named contexts
- **Rich output formats** - Table (default), JSON, YAML, CSV, and wide mode
- **OAuth2 authentication** - Automatic token management with refresh
- **Bulk operations** - Process multiple resources from CSV/YAML files
- **Template system** - Jinja2-style variable substitution for manifests
- **Permissions analysis** - Calculate effective permissions for users and groups
- **RACI matrix generation** - Generate governance matrices from IAM data
- **Management zones** - Zone operations and group comparison
- **Caching** - In-memory cache with TTL for reduced API calls

## Installation

```bash
# From source
pip install -e .

# Or install dependencies and use directly
pip install typer[all] httpx pydantic pyyaml rich platformdirs
```

## Quick Start

### 1. Set up credentials

```bash
# Add OAuth2 credentials
dtiam config set-credentials prod \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET

# Create a context
dtiam config set-context prod \
  --account-uuid YOUR_ACCOUNT_UUID \
  --credentials-ref prod

# Switch to the context
dtiam config use-context prod

# Verify configuration
dtiam config view
```

### 2. List resources

```bash
# List all groups
dtiam get groups

# List policies
dtiam get policies

# List users
dtiam get users

# List environments
dtiam get environments
```

### 3. Get detailed information

```bash
# Describe a group (includes members and policies)
dtiam describe group "DevOps Team"

# Describe a policy (includes statements)
dtiam describe policy "admin-policy"

# Describe a user (includes group memberships)
dtiam describe user user@example.com
```

### 4. Create resources

```bash
# Create a group
dtiam create group --name "New Team" --description "A new team"

# Create a binding (assign policy to group)
dtiam create binding --group "New Team" --policy "viewer-policy"
```

## Commands

| Command | Description |
|---------|-------------|
| `config` | Manage configuration contexts and credentials |
| `get` | List/retrieve resources |
| `describe` | Show detailed resource information |
| `create` | Create resources |
| `delete` | Delete resources |
| `user` | User management operations |
| `bulk` | Bulk operations for multiple resources |
| `template` | Template-based resource creation |
| `zones` | Management zone operations |
| `analyze` | Analyze permissions and policies |
| `raci` | RACI matrix generation |
| `export` | Export resources and data |
| `group` | Advanced group operations |
| `boundary` | Boundary attach/detach operations |
| `cache` | Cache management |

## Resources

| Resource | Description |
|----------|-------------|
| `groups` | IAM groups for organizing users |
| `policies` | Permission policies with statements |
| `users` | User accounts (read-only) |
| `bindings` | Policy-to-group assignments |
| `environments` | Dynatrace environments |
| `boundaries` | Scope restrictions for bindings |

## Global Options

```bash
dtiam [OPTIONS] COMMAND

Options:
  -c, --context TEXT    Override the current context
  -o, --output FORMAT   Output format: table, json, yaml, csv, wide
  -v, --verbose         Enable verbose/debug output
  --plain               Plain output mode (no colors, no prompts)
  --dry-run             Preview changes without applying them
  -V, --version         Show version and exit
  --help                Show help and exit
```

## Configuration

Configuration is stored at `~/.config/dtiam/config` (XDG Base Directory compliant).

```yaml
api-version: v1
kind: Config
current-context: production
contexts:
  - name: production
    context:
      account-uuid: abc-123-def
      credentials-ref: prod-creds
  - name: development
    context:
      account-uuid: xyz-789-uvw
      credentials-ref: dev-creds
credentials:
  - name: prod-creds
    credential:
      client-id: dt0s01.XXXXX
      client-secret: dt0s01.XXXXX.YYYYY
preferences:
  output: table
```

## Examples

### Bulk Operations

```bash
# Add multiple users to a group from CSV
dtiam bulk add-users --group "DevOps" --file users.csv

# Remove users from group
dtiam bulk remove-users --group "DevOps" --file users.csv

# Create resources from YAML
dtiam bulk create --file resources.yaml
```

### Template System

```bash
# List available templates
dtiam template list

# Render a template with variables
dtiam template render team-setup \
  --var team_name="Platform" \
  --var policy_level="admin"

# Apply rendered template
dtiam template apply team-setup \
  --var team_name="Platform" \
  --var policy_level="admin"
```

### Permissions Analysis

```bash
# Get effective permissions for a user
dtiam analyze user-permissions user@example.com

# Get effective permissions for a group
dtiam analyze group-permissions "DevOps Team"

# Generate permissions matrix
dtiam analyze permissions-matrix -o json > matrix.json
```

### RACI Matrix

```bash
# Generate basic RACI matrix
dtiam raci generate

# Generate enterprise RACI with custom mapping
dtiam raci generate --template enterprise -o yaml
```

### Export

```bash
# Export everything
dtiam export all --output-dir ./backup

# Export specific group with dependencies
dtiam export group "DevOps Team" --include-policies --include-members
```

### Management Zones

```bash
# List all zones
dtiam zones list

# Compare zones with groups
dtiam zones compare-groups
```

### Cache Management

```bash
# View cache statistics
dtiam cache stats

# Clear expired entries
dtiam cache clear --expired-only

# Clear all cache
dtiam cache clear --force
```

## Documentation

- [Quick Start Guide](docs/QUICK_START.md) - Detailed getting started guide
- [Command Reference](docs/COMMANDS.md) - Full command documentation
- [Architecture](docs/ARCHITECTURE.md) - Technical design and implementation
- [API Reference](docs/API_REFERENCE.md) - Programmatic usage

## Requirements

- Python 3.10+
- Dynatrace Account with API access
- OAuth2 client credentials with IAM permissions

## License

MIT License - see LICENSE file for details.
