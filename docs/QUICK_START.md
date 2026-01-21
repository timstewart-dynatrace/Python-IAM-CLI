# Quick Start Guide

> **DISCLAIMER:** This tool is provided "as-is" without warranty. Use at your own risk. This is an independent, community-developed tool and is **NOT produced, endorsed, or supported by Dynatrace**.

This guide walks you through setting up dtiam and performing common IAM management tasks.

## Prerequisites

- Python 3.10 or higher
- Dynatrace account with Account Management API access
- Authentication credentials (choose one):
  - **OAuth2 client credentials** (recommended for automation)
  - **Bearer token** (for quick testing/interactive use)

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/jtimothystewart/Python-IAM-CLI.git
cd Python-IAM-CLI

# Install in development mode
pip install -e .

# Verify installation
dtiam --version
```

### Dependencies Only

```bash
pip install typer[all] httpx pydantic pyyaml rich platformdirs
```

## Authentication

dtiam supports two authentication methods:

### Option 1: OAuth2 Client Credentials (Recommended)

**Best for:** Automation, scripts, CI/CD, long-running processes

OAuth2 is the recommended authentication method because tokens automatically refresh when expired, making it reliable for unattended operation.

#### Required OAuth2 Scopes

Your OAuth2 client needs the following scopes for full functionality:

| Scope | Purpose |
|-------|---------|
| `account-idm-read` | List and describe groups, users, bindings |
| `account-idm-write` | Create, update, delete groups, users, and bindings |
| `iam-policies-management` | Manage policies |
| `account-env-read` | List environments |
| `iam:effective-permissions:read` | Query effective permissions via resolution API |

#### Step 1: Create OAuth2 Credentials

1. Go to Account Management → Identity & access management → OAuth clients
2. Create a new client with the required scopes
3. Save the client ID and secret

#### Step 2: Configure dtiam (Config File Method)

```bash
# Add your credentials
dtiam config set-credentials myaccount \
  --client-id dt0s01.YOUR_CLIENT_ID \
  --client-secret dt0s01.YOUR_CLIENT_ID.YOUR_SECRET

# Create a context pointing to your account
dtiam config set-context myaccount \
  --account-uuid YOUR_ACCOUNT_UUID \
  --credentials-ref myaccount

# Activate the context
dtiam config use-context myaccount
```

#### Alternative: Environment Variables (OAuth2)

```bash
export DTIAM_CLIENT_ID="dt0s01.YOUR_CLIENT_ID"
export DTIAM_CLIENT_SECRET="dt0s01.YOUR_CLIENT_ID.YOUR_SECRET"
export DTIAM_ACCOUNT_UUID="YOUR_ACCOUNT_UUID"
```

### Option 2: Bearer Token (Static)

**Best for:** Quick testing, debugging, interactive sessions, one-off operations

> ⚠️ **WARNING:** Bearer tokens do NOT auto-refresh. When the token expires, all requests will fail with 401 Unauthorized. This method is NOT recommended for automation or scripts.

```bash
# Set bearer token via environment variable
export DTIAM_BEARER_TOKEN="dt0c01.YOUR_TOKEN_HERE..."
export DTIAM_ACCOUNT_UUID="YOUR_ACCOUNT_UUID"

# Run commands (token will be used until it expires)
dtiam get groups
```

**Risks of Bearer Token Authentication:**
- ❌ No automatic token refresh
- ❌ Silent failures when token expires
- ❌ Not suitable for automation
- ❌ Requires manual token renewal

### Authentication Priority

When multiple methods are configured, dtiam uses this priority:
1. `DTIAM_BEARER_TOKEN` + `DTIAM_ACCOUNT_UUID`
2. `DTIAM_CLIENT_ID` + `DTIAM_CLIENT_SECRET` + `DTIAM_ACCOUNT_UUID`
3. Config file context

### Verify Configuration

```bash
# View current configuration
dtiam config view

# Test connectivity by listing environments
dtiam get environments
```

## Common Tasks

### Listing Resources

```bash
# List all groups
dtiam get groups

# List with JSON output
dtiam get groups -o json

# List with additional columns
dtiam get groups -o wide

# Filter by name (partial match)
dtiam get groups --name "LOB5"
```

### Viewing Resource Details

```bash
# Describe a group (by name or UUID)
dtiam describe group "LOB5"

# Describe shows:
# - Basic info (UUID, name, description)
# - Member count and list
# - Assigned policies
# - Effective permissions

# Describe a policy
dtiam describe policy "admin-policy"

# Describe a user
dtiam describe user admin@company.com
```

### Creating Resources

#### Create a Group

```bash
# Simple group creation
dtiam create group --name "LOB5"

# With description
dtiam create group \
  --name "LOB5" \
  --description "LOB5 team with standard access"

# Preview without creating (dry-run)
dtiam --dry-run create group --name "Test Group"
```

#### Create a Policy Binding

```bash
# Assign a policy to a group
dtiam create binding \
  --group "LOB5" \
  --policy "developer-policy"

# With boundary restriction
dtiam create binding \
  --group "LOB5" \
  --policy "admin-policy" \
  --boundary "production-boundary"
```

### Deleting Resources

```bash
# Delete a group (with confirmation)
dtiam delete group "Test Group"

# Skip confirmation
dtiam delete group "Test Group" --force

# Delete a binding
dtiam delete binding \
  --group "LOB5" \
  --policy "developer-policy"
```

### User Management

```bash
# Create a new user
dtiam user create --email user@example.com

# Create with name and groups
dtiam user create \
  --email user@example.com \
  --first-name John \
  --last-name Doe \
  --groups "LOB5,LOB6"

# Delete a user
dtiam user delete user@example.com

# Delete without confirmation
dtiam user delete user@example.com --force

# Add a user to a group
dtiam user add-to-group --user user@example.com --group "LOB5"

# Remove from group
dtiam user remove-from-group --user user@example.com --group "LOB5"

# List user's groups
dtiam user list-groups user@example.com

# View user details
dtiam user info user@example.com
```

### Service User Management

Service users are OAuth clients used for programmatic API access.

```bash
# List all service users
dtiam get service-users

# Get a specific service user
dtiam get service-users "CI Pipeline"

# Create a service user (SAVE THE CREDENTIALS!)
dtiam create service-user --name "CI Pipeline"

# Create with groups and save credentials to file
dtiam create service-user \
  --name "CI Pipeline" \
  --description "CI/CD automation" \
  --groups "LOB5,LOB6" \
  --save-credentials creds.json

# Update a service user
dtiam service-user update "CI Pipeline" --description "Updated description"

# Add to group
dtiam service-user add-to-group --user "CI Pipeline" --group LOB5

# Remove from group
dtiam service-user remove-from-group --user "CI Pipeline" --group LOB5

# List groups
dtiam service-user list-groups "CI Pipeline"

# Delete a service user
dtiam delete service-user "CI Pipeline"
```

### Account Information

View account limits and subscription information.

```bash
# View account limits and quotas
dtiam account limits

# Check capacity before adding resources
dtiam account check-capacity maxUsers
dtiam account check-capacity maxGroups --count 5

# List subscriptions
dtiam account subscriptions

# Get subscription details
dtiam account subscription my-subscription

# Get usage forecast
dtiam account forecast

# List subscription capabilities
dtiam account capabilities
```

## Advanced Operations

### Bulk Operations

#### Add Multiple Users

Create a CSV file `users.csv`:
```csv
email
user1@example.com
user2@example.com
user3@example.com
```

```bash
dtiam bulk add-users --group "LOB5" --file users.csv
```

#### Create Multiple Resources

Create a YAML file `resources.yaml`:
```yaml
groups:
  - name: Team Alpha
    description: Alpha team
  - name: Team Beta
    description: Beta team

bindings:
  - group: Team Alpha
    policy: developer-policy
  - group: Team Beta
    policy: viewer-policy
```

```bash
dtiam bulk create --file resources.yaml
```

### Template System

Templates allow reusable resource definitions with variables.

#### List Available Templates

```bash
dtiam template list
```

#### Create a Custom Template

Create `~/.config/dtiam/templates/team-onboard.yaml`:
```yaml
name: team-onboard
description: Onboard a new team with standard setup
variables:
  - name: team_name
    description: Name of the team
    required: true
  - name: team_lead
    description: Team lead email
    required: true
resources:
  groups:
    - name: "{{ team_name }}"
      description: "{{ team_name }} team group"
  bindings:
    - group: "{{ team_name }}"
      policy: developer-policy
```

#### Apply a Template

```bash
# Preview the rendered template
dtiam template render team-onboard \
  --var team_name="LOB5" \
  --var team_lead="lead@example.com"

# Apply the template
dtiam template apply team-onboard \
  --var team_name="LOB5" \
  --var team_lead="lead@example.com"
```

### Permissions Analysis

#### Effective Permissions (Resolution API)

Query the Dynatrace resolution API for effective permissions:

```bash
# Get effective permissions for a user
dtiam analyze effective-user admin@example.com

# Get effective permissions for a group
dtiam analyze effective-group "LOB5"

# Filter by services
dtiam analyze effective-user admin@example.com --services "settings,automation"

# Specify level (account or environment)
dtiam analyze effective-user admin@example.com --level environment --level-id env-id

# Export to file
dtiam analyze effective-user admin@example.com --export permissions.json

# JSON output for processing
dtiam analyze effective-user admin@example.com -o json
```

#### Calculated Permissions

Analyze permissions from policies and bindings:

```bash
# See all permissions for a user
dtiam analyze user-permissions admin@example.com

# JSON output for processing
dtiam analyze user-permissions admin@example.com -o json
```

#### Group Effective Permissions

```bash
dtiam analyze group-permissions "LOB5"
```

#### Permissions Matrix

Generate a matrix showing which groups have which permissions:

```bash
# Table format
dtiam analyze permissions-matrix

# Export as JSON
dtiam analyze permissions-matrix -o json > matrix.json
```

### Management Zones (Legacy)

> **DEPRECATION NOTICE:** Management Zone features are provided for legacy purposes only and will be removed in a future release. Dynatrace is transitioning away from management zones in favor of other access control mechanisms.

```bash
# List all management zones
dtiam zones list

# Get zone details
dtiam zones get "Production Zone"

# Compare zones with groups (find naming mismatches)
dtiam zones compare-groups
```

### Export Operations

#### Full Backup

```bash
# Export everything to a directory
dtiam export all --output-dir ./iam-backup

# This creates:
# ./iam-backup/groups.yaml
# ./iam-backup/policies.yaml
# ./iam-backup/bindings.yaml
# ./iam-backup/users.yaml
# ./iam-backup/environments.yaml
```

#### Selective Export

```bash
# Export a single group with dependencies
dtiam export group "LOB5" \
  --include-policies \
  --include-members \
  -o yaml > devops-team.yaml
```

### Group Operations

#### Clone a Group

```bash
# Clone with policies but not members
dtiam group clone "LOB5" \
  --new-name "LOB5 - Staging"

# Clone with members
dtiam group clone "LOB5" \
  --new-name "LOB5 - Copy" \
  --include-members
```

#### Quick Setup

```bash
# Create group with policy in one command
dtiam group setup "New Team" \
  --policy "developer-policy" \
  --description "Newly created team"
```

### Boundary Management

```bash
# Attach a boundary to a binding
dtiam boundary attach \
  --group "LOB5" \
  --policy "admin-policy" \
  --boundary "production-boundary"

# Detach a boundary
dtiam boundary detach \
  --group "LOB5" \
  --policy "admin-policy" \
  --boundary "production-boundary"

# List all bindings using a boundary
dtiam boundary list-attached "production-boundary"
```

### Cache Management

dtiam caches API responses to reduce latency and API calls:

```bash
# View cache statistics
dtiam cache stats

# Clear expired entries only
dtiam cache clear --expired-only

# Clear entries by prefix
dtiam cache clear --prefix groups

# Clear all cache
dtiam cache clear --force

# View cache keys
dtiam cache keys

# Adjust default TTL (seconds)
dtiam cache set-ttl 600
```

## Output Formats

dtiam supports multiple output formats:

| Format | Flag | Description |
|--------|------|-------------|
| Table | `-o table` | Human-readable tables (default) |
| JSON | `-o json` | JSON for programmatic use |
| YAML | `-o yaml` | YAML for configuration files |
| CSV | `-o csv` | CSV for spreadsheets |
| Wide | `-o wide` | Table with additional columns |

### Examples

```bash
# JSON output for scripting
dtiam get groups -o json | jq '.[] | .name'

# YAML for backup
dtiam get policies -o yaml > policies.yaml

# CSV for Excel
dtiam get users -o csv > users.csv
```

## Working with Multiple Accounts

### Configure Multiple Contexts

```bash
# Production account
dtiam config set-credentials prod \
  --client-id dt0s01.PROD_ID \
  --client-secret dt0s01.PROD_ID.PROD_SECRET

dtiam config set-context production \
  --account-uuid PROD_UUID \
  --credentials-ref prod

# Development account
dtiam config set-credentials dev \
  --client-id dt0s01.DEV_ID \
  --client-secret dt0s01.DEV_ID.DEV_SECRET

dtiam config set-context development \
  --account-uuid DEV_UUID \
  --credentials-ref dev
```

### Switch Contexts

```bash
# Switch default context
dtiam config use-context production

# One-time context override
dtiam --context development get groups

# Check current context
dtiam config current-context
```

## Troubleshooting

### Enable Verbose Output

```bash
dtiam -v get groups
```

This shows:
- API requests and responses
- Token acquisition details
- Timing information

### Dry Run Mode

Preview changes without applying:

```bash
dtiam --dry-run create group --name "Test"
dtiam --dry-run delete group "Old Group"
dtiam --dry-run bulk create --file resources.yaml
```

### Common Errors

**Authentication Failed**
```
Error: Failed to acquire OAuth token
```
- Verify client ID and secret
- Check OAuth2 scopes
- Ensure credentials-ref matches a valid credential

**Resource Not Found**
```
Error: Group 'XYZ' not found
```
- Check spelling and case sensitivity
- Use `dtiam get groups` to list available groups
- Try using UUID instead of name

**Permission Denied**
```
Error: 403 Forbidden
```
- Verify OAuth2 scopes include required permissions
- Check if resource is in a different environment

### Reset Configuration

```bash
# View config file location
dtiam config view

# Remove configuration
rm -rf ~/.config/dtiam
```

## Next Steps

- [Command Reference](COMMANDS.md) - Complete command documentation
- [Architecture](ARCHITECTURE.md) - Technical implementation details
- [API Reference](API_REFERENCE.md) - Programmatic usage guide
