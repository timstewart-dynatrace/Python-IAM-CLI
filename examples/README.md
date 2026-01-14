# Examples

This directory contains example configurations and scripts demonstrating how to use the dtiam CLI.

> **DISCLAIMER:** This tool is provided "as-is" without warranty. Use at your own risk. This is an independent, community-developed tool and is **NOT produced, endorsed, or supported by Dynatrace**.

## Directory Structure

```
examples/
├── auth/           # Authentication configuration
├── boundaries/     # Policy boundary examples
├── bulk/           # Bulk operation sample files
├── config/         # Multi-account configuration examples
├── groups/         # Group configuration examples
├── policies/       # Policy configuration examples
├── service-users/  # Service user (OAuth client) examples
├── templates/      # Reusable template examples
├── scripts/        # Shell script examples
└── README.md
```

## Subdirectories

### `auth/` - Authentication

OAuth2 and bearer token configuration examples:

| File | Description |
|------|-------------|
| `.env.example` | Environment variable configuration template |

**Setup:**

```bash
cp examples/auth/.env.example .env
nano .env  # Edit with your credentials
source .env
```

**Required Variables (OAuth2 - Recommended):**

- `DTIAM_CLIENT_ID` - OAuth2 client ID
- `DTIAM_CLIENT_SECRET` - OAuth2 client secret
- `DTIAM_ACCOUNT_UUID` - Dynatrace account UUID

**Alternative (Bearer Token):**

- `DTIAM_BEARER_TOKEN` - Static bearer token (does NOT auto-refresh)
- `DTIAM_ACCOUNT_UUID` - Dynatrace account UUID

### `boundaries/` - Policy Boundary Examples

Boundary configurations for zone-scoped access control:

| File | Description |
|------|-------------|
| `production-only.yaml` | Restrict access to production zones |
| `team-scoped.yaml` | Team-specific zone restrictions |

**Usage:**

```bash
# Create a production-only boundary
dtiam create boundary --name "production-only" --zones "Production,Prod-US,Prod-EU"

# Bind policy with boundary restriction
dtiam create binding --group "Prod-Admins" --policy "Admin User" --boundary "production-only"
```

### `bulk/` - Bulk Operation Files

Sample files for bulk CLI operations:

| File | Description |
|------|-------------|
| `sample_users.csv` | Sample CSV for `dtiam bulk add-users-to-group` |
| `sample_groups.yaml` | Sample YAML for `dtiam bulk create-groups` |
| `sample_bindings.yaml` | Sample YAML for `dtiam bulk create-bindings` |
| `sample_bulk_groups.csv` | Sample CSV for `dtiam bulk create-groups-with-policies` (all-in-one) |

**Usage:**

```bash
# Add multiple users to a group
dtiam bulk add-users-to-group --file examples/bulk/sample_users.csv --group "DevOps Team"

# Create multiple groups
dtiam bulk create-groups --file examples/bulk/sample_groups.yaml

# Create multiple bindings
dtiam bulk create-bindings --file examples/bulk/sample_bindings.yaml

# Create groups with policies and bindings (all-in-one operation)
dtiam bulk create-groups-with-policies --file examples/bulk/sample_bulk_groups.csv
```

**CSV Format for `sample_bulk_groups.csv`:**

The all-in-one CSV format creates groups, boundaries, and bindings together:

```csv
group_name,policy_name,level,level_id,management_zones,boundary_name,description
LOB5,Standard User - Config,account,,,,LOB5 team - global read
LOB5,Pro User,environment,abc12345,LOB5,LOB5-Boundary,LOB5 restricted write
```

**Features:**
- Creates groups if they don't exist
- Creates boundaries with management zones
- Creates policy bindings at account or environment level
- Idempotent (skips existing resources)

### `config/` - Configuration Examples

Multi-account configuration examples:

| File | Description |
|------|-------------|
| `multi-account.yaml` | Sample config for managing multiple Dynatrace accounts |

**Usage:**

```bash
# Copy to config location
cp examples/config/multi-account.yaml ~/.config/dtiam/config

# Or set up step by step
dtiam config set-credentials prod-creds --client-id dt0s01.XXX --client-secret dt0s01.XXX.YYY
dtiam config set-context production --account-uuid abc-123 --credentials-ref prod-creds
dtiam config use-context production

# Switch between contexts
dtiam config use-context staging
dtiam -c production get groups  # Override for single command
```

### `groups/` - Group Examples

Pre-built group configurations that can be used as references:

| File | Description |
|------|-------------|
| `team-group.yaml` | Standard team group template |
| `admin-group.yaml` | Administrator group with full access |
| `readonly-group.yaml` | Read-only access group |

**Usage:**

```bash
# View group configuration
cat examples/groups/team-group.yaml

# Create group based on example
dtiam create group --name "My Team" --description "My team description"
```

### `policies/` - Policy Examples

Pre-built policy templates with common permission patterns:

| File | Description |
|------|-------------|
| `viewer-policy.yaml` | Read-only access policy |
| `devops-policy.yaml` | DevOps team permissions |
| `slo-manager.yaml` | SLO management permissions |
| `settings-writer.yaml` | Settings write access |

**Usage:**

```bash
# View policy statement
cat examples/policies/viewer-policy.yaml

# Create policy from example
dtiam create policy --name "viewer" --statement "ALLOW settings:objects:read;"
```

See `policies/README.md` for complete list and descriptions.

### `service-users/` - Service User Examples

Service user (OAuth client) configurations for automation:

| File | Description |
|------|-------------|
| `ci-pipeline.yaml` | CI/CD automation service user |
| `monitoring-bot.yaml` | Read-only monitoring service user |

**Usage:**

```bash
# Create a service user for CI/CD
dtiam service-user create --name "ci-pipeline" \
  --description "Service user for CI/CD automation" \
  --save-credentials ci-creds.json

# Create with group membership
dtiam service-user create --name "monitoring-bot" \
  --groups "Observers" \
  --save-credentials monitoring-creds.json
```

**Important:** Save the client secret immediately - it cannot be retrieved later!

### `templates/` - Reusable Templates

Templates for the dtiam template system:

| File | Description |
|------|-------------|
| `group-team.yaml` | Team group template with variables |
| `policy-readonly.yaml` | Read-only policy template |

**Usage:**

```bash
# List available templates
dtiam template list

# Save custom template
dtiam template save my-template --kind Group --file examples/templates/group-team.yaml

# Apply template with variables
dtiam template apply group-team --var team_name=platform --var description="Platform Team"
```

### `scripts/` - Shell Script Examples

Shell scripts demonstrating common workflows:

| File | Description |
|------|-------------|
| `example_cli_lifecycle.sh` | Full IAM lifecycle validation |
| `example_common_workflows.sh` | Common workflow examples |

**Usage:**

```bash
# Run lifecycle validation (dry-run)
bash examples/scripts/example_cli_lifecycle.sh

# Run with actual changes
bash examples/scripts/example_cli_lifecycle.sh --execute

# Show common workflows
bash examples/scripts/example_common_workflows.sh
```

## Quick Start

### 1. Set Up Authentication

```bash
# Option A: Using environment variables
cp examples/auth/.env.example .env
nano .env  # Add your credentials
source .env

# Option B: Using config file
dtiam config set-credentials prod-creds --client-id dt0s01.XXX --client-secret dt0s01.XXX.YYY
dtiam config set-context prod --account-uuid abc-123-def --credentials-ref prod-creds --current
```

### 2. Verify Connection

```bash
dtiam get groups
```

### 3. Explore Examples

```bash
# List groups
dtiam get groups

# Create a group
dtiam create group --name "Test Group" --description "Test description"

# Create a policy
dtiam create policy --name "test-viewer" --statement "ALLOW settings:objects:read;"

# Bind policy to group
dtiam create binding --group "Test Group" --policy "test-viewer"
```

## API Credentials

### Getting OAuth2 Credentials

1. Go to your Dynatrace Account
2. Navigate to **Identity & access management** > **OAuth clients**
3. Click **Create client**
4. Select required scopes:
   - `account-idm-read` / `account-idm-write`
   - `iam-policies-management`
   - `account-env-read`
   - `iam:effective-permissions:read` (for effective permissions)
5. Copy the credentials:
   - Client ID
   - Client Secret
   - Account UUID

### Required OAuth2 Scopes

| Scope | Description |
|-------|-------------|
| `account-idm-read` | Read users, groups, service users |
| `account-idm-write` | Create/update/delete users, groups |
| `iam-policies-management` | Manage policies and bindings |
| `account-env-read` | Read environments |
| `iam:effective-permissions:read` | Query effective permissions |
| `iam:boundaries:read` | Read policy boundaries |
| `iam:boundaries:write` | Create/update/delete boundaries |
| `iam:limits:read` | Read account limits |

## Security

**Important:**

- `.env` files are in `.gitignore` - never commit real credentials
- Store credentials locally only
- Use OAuth2 for automation (auto-refreshes tokens)
- Bearer tokens do NOT auto-refresh and will fail when expired

## Error Handling

Common issues:

- **"No context configured"** - Run `dtiam config set-context` and `dtiam config use-context`
- **"Permission denied"** - Check OAuth2 scopes
- **"Token expired"** - Use OAuth2 instead of bearer token for automation
- **"Resource not found"** - Verify UUID or name exists

## Troubleshooting

### Environment variables not loading

```bash
# Check variables are set
echo $DTIAM_CLIENT_ID
echo $DTIAM_ACCOUNT_UUID

# Verify from CLI
dtiam -v get groups
```

### Config file issues

```bash
# Check config path
dtiam config path

# View current config
dtiam config view

# List contexts
dtiam config get-contexts
```

## Documentation

- [README.md](../README.md) - Overview and quick start
- [docs/QUICK_START.md](../docs/QUICK_START.md) - Detailed getting started
- [docs/COMMANDS.md](../docs/COMMANDS.md) - Full command reference
- [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) - Technical design
- [docs/API_REFERENCE.md](../docs/API_REFERENCE.md) - Programmatic usage
