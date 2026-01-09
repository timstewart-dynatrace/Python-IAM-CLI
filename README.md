# dtiam - Dynatrace IAM CLI

> **DISCLAIMER:** This tool is provided "as-is" without warranty. Use at your own risk. This is an independent, community-developed tool and is **NOT produced, endorsed, or supported by Dynatrace**. For official Dynatrace tools and support, please visit [dynatrace.com](https://www.dynatrace.com).

A kubectl-inspired command-line interface for managing Dynatrace Identity and Access Management resources.

## Features

- **kubectl-style commands** - Familiar syntax: `get`, `describe`, `create`, `delete`, `apply`
- **Multi-context configuration** - Manage multiple Dynatrace accounts with named contexts
- **Rich output formats** - Table (default), JSON, YAML, CSV, and wide mode
- **OAuth2 authentication** - Automatic token management with refresh
- **Bulk operations** - Process multiple resources from CSV/YAML files
- **Template system** - Jinja2-style variable substitution for manifests
- **Permissions analysis** - Calculate effective permissions for users and groups
- **Management zones** - Zone operations and group comparison *(legacy - see deprecation notice)*
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
| `service-user` | Service user (OAuth client) management |
| `account` | Account limits and subscriptions |
| `bulk` | Bulk operations for multiple resources |
| `template` | Template-based resource creation |
| `zones` | Management zone operations *(legacy)* |
| `analyze` | Analyze permissions and policies |
| `export` | Export resources and data |
| `group` | Advanced group operations |
| `boundary` | Boundary attach/detach operations |
| `cache` | Cache management |

## Resources

| Resource | Description |
|----------|-------------|
| `groups` | IAM groups for organizing users |
| `policies` | Permission policies with statements |
| `users` | User accounts |
| `service-users` | Service users (OAuth clients) for automation |
| `bindings` | Policy-to-group assignments |
| `environments` | Dynatrace environments |
| `boundaries` | Scope restrictions for bindings |
| `limits` | Account limits and quotas |
| `subscriptions` | Account subscriptions |

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

### Export

```bash
# Export everything
dtiam export all --output-dir ./backup

# Export specific group with dependencies
dtiam export group "DevOps Team" --include-policies --include-members
```

### Management Zones (Legacy)

> **DEPRECATION NOTICE:** Management Zone features are provided for legacy purposes only and will be removed in a future release. Dynatrace is transitioning away from management zones in favor of other access control mechanisms.

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

## Required OAuth2 Scopes

Your OAuth2 client needs specific scopes for each operation. Create your client at:
**Account Management → Identity & access management → OAuth clients**

### Scope Reference by Command

| Command | Operation | Required Scopes |
|---------|-----------|-----------------|
| **Groups** | | |
| `get groups` | List/get groups | `account-idm-read` |
| `create group` | Create group | `account-idm-write` |
| `delete group` | Delete group | `account-idm-write` |
| `group clone` | Clone group | `account-idm-read`, `account-idm-write` |
| **Users** | | |
| `get users` | List/get users | `account-idm-read` |
| `user create` | Create user | `account-idm-write` |
| `user delete` | Delete user | `account-idm-write` |
| `user add-to-group` | Add to group | `account-idm-write` |
| `user remove-from-group` | Remove from group | `account-idm-write` |
| **Service Users** | | |
| `service-user list` | List service users | `account-idm-read` |
| `service-user create` | Create service user | `account-idm-write` |
| `service-user update` | Update service user | `account-idm-write` |
| `service-user delete` | Delete service user | `account-idm-write` |
| **Policies** | | |
| `get policies` | List/get policies | `iam-policies-management` or `iam:policies:read` |
| `create policy` | Create policy | `iam-policies-management` or `iam:policies:write` |
| `delete policy` | Delete policy | `iam-policies-management` or `iam:policies:write` |
| **Bindings** | | |
| `get bindings` | List bindings | `iam-policies-management` or `iam:bindings:read` |
| `create binding` | Create binding | `iam-policies-management` or `iam:bindings:write` |
| `delete binding` | Delete binding | `iam-policies-management` or `iam:bindings:write` |
| **Boundaries** | | |
| `get boundaries` | List/get boundaries | `iam-policies-management` or `iam:boundaries:read` |
| `create boundary` | Create boundary | `iam-policies-management` or `iam:boundaries:write` |
| `delete boundary` | Delete boundary | `iam-policies-management` or `iam:boundaries:write` |
| `boundary attach/detach` | Modify bindings | `iam-policies-management` or `iam:bindings:write` |
| **Analysis** | | |
| `analyze effective-user` | Effective permissions | `iam:effective-permissions:read` |
| `analyze effective-group` | Effective permissions | `iam:effective-permissions:read` |
| **Account** | | |
| `account limits` | Account limits | `account-idm-read` |
| `account subscriptions` | Subscriptions | Bearer token (auto) |
| **Environments** | | |
| `get environments` | List environments | `account-env-read` |
| `zones list` | Management zones | `account-env-read` |

### Recommended Scope Sets

**Read-Only Access:**
```
account-idm-read
account-env-read
iam:policies:read
iam:bindings:read
iam:boundaries:read
iam:effective-permissions:read
```

**Full IAM Management:**
```
account-idm-read
account-idm-write
account-env-read
iam-policies-management
iam:effective-permissions:read
```

## Requirements

- Python 3.10+
- Dynatrace Account with API access
- OAuth2 client credentials with appropriate scopes (see above)

## Disclaimer

**USE AT YOUR OWN RISK.** This tool is provided "as-is" without any warranty of any kind, express or implied. The authors and contributors are not responsible for any damages or data loss that may result from using this tool.

**NOT PRODUCED BY DYNATRACE.** This is an independent, community-developed tool. It is not produced, endorsed, maintained, or supported by Dynatrace. For official Dynatrace products and support, visit [dynatrace.com](https://www.dynatrace.com).

**NO SUPPORT PROVIDED.** This tool is provided without support. Issues may be reported via GitHub, but there is no guarantee of response or resolution.

## License

MIT License - see LICENSE file for details.
