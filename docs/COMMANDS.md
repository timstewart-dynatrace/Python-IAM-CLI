# Command Reference

> **DISCLAIMER:** This tool is provided "as-is" without warranty. Use at your own risk. This is an independent, community-developed tool and is **NOT produced, endorsed, or supported by Dynatrace**.

Complete reference for all dtiam commands and their options.

## Table of Contents

- [Global Options](#global-options)
- [Environment Variables](#environment-variables)
- [config](#config) - Configuration management
- [get](#get) - List/retrieve resources
- [describe](#describe) - Detailed resource information
- [create](#create) - Create resources
- [delete](#delete) - Delete resources
- [user](#user) - User management
- [bulk](#bulk) - Bulk operations
- [template](#template) - Template system
- [zones](#zones) - Management zones _(legacy)_
- [analyze](#analyze) - Permissions analysis
- [export](#export) - Export resources
- [group](#group) - Advanced group operations
- [boundary](#boundary) - Boundary management
- [cache](#cache) - Cache management
- [service-user](#service-user) - Service user (OAuth client) management
- [account](#account) - Account limits and subscriptions

---

## Global Options

These options apply to all commands:

```bash
dtiam [OPTIONS] COMMAND [ARGS]
```

| Option            | Short | Description                                 |
| ----------------- | ----- | ------------------------------------------- |
| `--context TEXT`  | `-c`  | Override the current context                |
| `--output FORMAT` | `-o`  | Output format: table, json, yaml, csv, wide |
| `--verbose`       | `-v`  | Enable verbose/debug output                 |
| `--plain`         |       | Plain output mode (no colors, no prompts)   |
| `--dry-run`       |       | Preview changes without applying them       |
| `--version`       | `-V`  | Show version and exit                       |
| `--help`          |       | Show help message                           |

---

## Environment Variables

dtiam supports authentication and configuration via environment variables:

### Authentication Variables

| Variable              | Description            | Use Case                 |
| --------------------- | ---------------------- | ------------------------ |
| `DTIAM_BEARER_TOKEN`  | Static bearer token    | Quick testing, debugging |
| `DTIAM_CLIENT_ID`     | OAuth2 client ID       | Automation (recommended) |
| `DTIAM_CLIENT_SECRET` | OAuth2 client secret   | Automation (recommended) |
| `DTIAM_ACCOUNT_UUID`  | Dynatrace account UUID | Required for all methods |

### Configuration Variables

| Variable                 | Description                                  |
| ------------------------ | -------------------------------------------- |
| `DTIAM_CONTEXT`          | Override current context name                |
| `DTIAM_OUTPUT`           | Default output format                        |
| `DTIAM_VERBOSE`          | Enable verbose mode                          |
| `DTIAM_ENVIRONMENT_URL`  | Environment URL for App Engine Registry      |
| `DTIAM_ENVIRONMENT_TOKEN`| Environment API token for management zones   |

### Authentication Priority

When multiple authentication methods are configured:

1. **Bearer Token** - `DTIAM_BEARER_TOKEN` + `DTIAM_ACCOUNT_UUID`
2. **OAuth2 (env)** - `DTIAM_CLIENT_ID` + `DTIAM_CLIENT_SECRET` + `DTIAM_ACCOUNT_UUID`
3. **Config file** - Context with OAuth2 credentials

### OAuth2 vs Bearer Token

| Feature          | OAuth2 (Recommended) | Bearer Token       |
| ---------------- | -------------------- | ------------------ |
| Auto-refresh     | ✅ Yes               | ❌ No              |
| Long-running     | ✅ Suitable          | ❌ Not recommended |
| Automation       | ✅ Recommended       | ❌ Not recommended |
| Quick testing    | ✅ Works             | ✅ Ideal           |
| Setup complexity | Medium               | Low                |

**Example: OAuth2 Authentication**

```bash
export DTIAM_CLIENT_ID="dt0s01.XXXXX"
export DTIAM_CLIENT_SECRET="dt0s01.XXXXX.YYYYY"
export DTIAM_ACCOUNT_UUID="abc-123-def"
dtiam get groups
```

**Example: Bearer Token Authentication**

```bash
# WARNING: Token will NOT auto-refresh!
export DTIAM_BEARER_TOKEN="dt0c01.XXXXX.YYYYY..."
export DTIAM_ACCOUNT_UUID="abc-123-def"
dtiam get groups
```

---

## config

Manage configuration contexts and credentials.

### config view

Display the current configuration.

```bash
dtiam config view [--show-secrets]
```

| Option           | Description                                 |
| ---------------- | ------------------------------------------- |
| `--show-secrets` | Show full credential values (security risk) |

### config get-contexts

List all configured contexts.

```bash
dtiam config get-contexts
```

### config current-context

Display the current context name.

```bash
dtiam config current-context
```

### config use-context

Switch to a different context.

```bash
dtiam config use-context NAME
```

| Argument | Description               |
| -------- | ------------------------- |
| `NAME`   | Context name to switch to |

### config set-context

Create or update a context.

```bash
dtiam config set-context NAME [OPTIONS]
```

| Argument/Option     | Short | Description                     |
| ------------------- | ----- | ------------------------------- |
| `NAME`              |       | Context name                    |
| `--account-uuid`    | `-a`  | Dynatrace account UUID          |
| `--credentials-ref` | `-c`  | Reference to a named credential |
| `--current`         |       | Set as current context          |

**Example:**

```bash
dtiam config set-context prod --account-uuid abc-123 --credentials-ref prod-creds --current
```

### config delete-context

Delete a context.

```bash
dtiam config delete-context NAME [--force]
```

| Option    | Short | Description       |
| --------- | ----- | ----------------- |
| `--force` | `-f`  | Skip confirmation |

### config set-credentials

Store OAuth2 credentials and environment settings. For existing credentials, only the provided fields are updated (partial update support).

**Client ID Auto-Extraction:** The client ID is automatically extracted from the client secret since Dynatrace secrets follow the format `dt0s01.CLIENTID.SECRETPART`. You only need to provide `--client-secret`.

```bash
dtiam config set-credentials NAME [OPTIONS]
```

| Argument/Option       | Short | Description                                          |
| --------------------- | ----- | ---------------------------------------------------- |
| `NAME`                |       | Credential name                                      |
| `--client-id`         | `-i`  | OAuth2 client ID (auto-extracted from secret if not provided) |
| `--client-secret`     | `-s`  | OAuth2 client secret (prompts if not provided for new) |
| `--account-uuid`      | `-a`  | Dynatrace account UUID (prompts if not provided for new) |
| `--environment-url`   | `-e`  | Dynatrace environment URL                            |
| `--environment-token` | `-t`  | Environment API token (for management zones)         |

**Examples:**

```bash
# Create new credentials (client ID auto-extracted from secret)
dtiam config set-credentials prod-creds \
  --client-secret dt0s01.XXX.YYY \
  --account-uuid abc-123 \
  --environment-url https://abc123.live.dynatrace.com

# Explicitly specify client ID (overrides auto-extraction)
dtiam config set-credentials prod-creds \
  --client-id dt0s01.XXX \
  --client-secret dt0s01.XXX.YYY \
  --account-uuid abc-123

# Update just the environment token (existing credential)
dtiam config set-credentials prod-creds --environment-token dt0c01.XXX

# Update environment URL only
dtiam config set-credentials prod-creds --environment-url https://new-env.live.dynatrace.com

# Interactive prompt for new credentials
dtiam config set-credentials dev-creds
```

### config delete-credentials

Delete stored credentials.

```bash
dtiam config delete-credentials NAME [--force]
```

### config get-credentials

List all stored credentials.

```bash
dtiam config get-credentials
```

### config path

Display the configuration file path.

```bash
dtiam config path
```

---

## get

List or retrieve IAM resources.

### Filtering

All `get` commands support **partial text matching** via filter options:

| Command | Filter | Behavior |
|---------|--------|----------|
| `get groups` | `--name` | Case-insensitive substring match |
| `get users` | `--email` | Case-insensitive substring match |
| `get policies` | `--name` | Case-insensitive substring match |
| `get boundaries` | `--name` | Case-insensitive substring match |
| `get environments` | `--name` | Case-insensitive substring match |
| `get apps` | `--name` | Case-insensitive substring match |
| `get schemas` | `--name` | Case-insensitive substring match (on ID or display name) |
| `get service-users` | `--name` | Case-insensitive substring match |

**Example:** `dtiam get groups --name LOB` returns groups named "LOB5", "LOB6", "MyLOBTeam", etc.

### get groups

List or get IAM groups.

```bash
dtiam get groups [IDENTIFIER] [OPTIONS]
```

| Argument/Option | Short | Description                   |
| --------------- | ----- | ----------------------------- |
| `IDENTIFIER`    |       | Group UUID or name (optional) |
| `--name`        | `-n`  | Filter by name                |
| `--output`      | `-o`  | Output format                 |

Aliases: `get group`

### get users

List or get IAM users.

```bash
dtiam get users [IDENTIFIER] [OPTIONS]
```

| Argument/Option | Short | Description                  |
| --------------- | ----- | ---------------------------- |
| `IDENTIFIER`    |       | User UID or email (optional) |
| `--email`       | `-e`  | Filter by email              |
| `--output`      | `-o`  | Output format                |

Aliases: `get user`

### get policies

List or get IAM policies.

By default, lists policies from all levels (account, global, and environments).
Use `--level` to filter to a specific level.

```bash
dtiam get policies [IDENTIFIER] [OPTIONS]
```

| Argument/Option | Short | Description                                                       |
| --------------- | ----- | ----------------------------------------------------------------- |
| `IDENTIFIER`    |       | Policy UUID or name (optional)                                    |
| `--name`        | `-n`  | Filter by name                                                    |
| `--level`       | `-l`  | Policy level: account, global, environment, or specific env ID   |
| `--output`      | `-o`  | Output format                                                     |

**Level options:**
- (default): All levels (account + global + all environments)
- `account`: Account-level custom policies only
- `global`: Dynatrace built-in policies only
- `environment`: All environment-level policies
- `<env-id>`: Policies for a specific environment ID

**Examples:**

```bash
# List all policies from all levels
dtiam get policies

# List only account-level policies
dtiam get policies --level account

# List only global (built-in) policies
dtiam get policies --level global

# List policies for a specific environment
dtiam get policies --level abc12345
```

Aliases: `get policy`

### get bindings

List IAM policy bindings.

By default, lists bindings from all levels (account, global, and environments).
Use `--level` to filter to a specific level.

```bash
dtiam get bindings [OPTIONS]
```

| Option     | Short | Description                                                       |
| ---------- | ----- | ----------------------------------------------------------------- |
| `--group`  | `-g`  | Filter by group UUID                                              |
| `--level`  | `-l`  | Binding level: account, global, environment, or specific env ID  |
| `--output` | `-o`  | Output format                                                     |

**Level options:**
- (default): All levels (account + global + all environments)
- `account`: Account-level bindings only
- `global`: Global bindings only
- `environment`: All environment-level bindings
- `<env-id>`: Bindings for a specific environment ID

**Examples:**

```bash
# List all bindings from all levels
dtiam get bindings

# List only account-level bindings
dtiam get bindings --level account

# List bindings for a specific group
dtiam get bindings --group 12345678-1234-1234-1234-123456789abc

# List bindings for a specific environment
dtiam get bindings --level abc12345
```

Aliases: `get binding`

### get environments

List or get Dynatrace environments.

```bash
dtiam get environments [IDENTIFIER] [OPTIONS]
```

| Argument/Option | Short | Description                           |
| --------------- | ----- | ------------------------------------- |
| `IDENTIFIER`    |       | Environment ID or name (optional)     |
| `--name`        | `-n`  | Filter by name (partial match)        |
| `--output`      | `-o`  | Output format                         |

**Examples:**

```bash
# Filter environments by name
dtiam get environments --name Prod
```

Aliases: `get envs`, `get env`

### get boundaries

List or get IAM policy boundaries.

```bash
dtiam get boundaries [IDENTIFIER] [OPTIONS]
```

| Argument/Option | Short | Description                      |
| --------------- | ----- | -------------------------------- |
| `IDENTIFIER`    |       | Boundary UUID or name (optional) |
| `--name`        | `-n`  | Filter by name                   |
| `--output`      | `-o`  | Output format                    |

Aliases: `get boundary`

### get apps

List or get Dynatrace Apps from the App Engine Registry.

```bash
dtiam get apps [IDENTIFIER] [OPTIONS]
```

| Argument/Option   | Short | Description                                     |
| ----------------- | ----- | ----------------------------------------------- |
| `IDENTIFIER`      |       | App ID or name (optional)                       |
| `--name`          | `-n`  | Filter by name (partial match)                  |
| `--environment`   | `-e`  | Environment ID or URL (required)                |
| `--ids`           |       | Output only app IDs (for use in policies)       |
| `--output`        | `-o`  | Output format                                   |

Aliases: `get app`

**Notes:**
- Requires an environment URL via `--environment` or `DTIAM_ENVIRONMENT_URL`
- App IDs can be used in policy/boundary statements: `shared:app-id = '{app.id}';`
- Environment can be specified as ID (e.g., `abc12345`) or full URL (e.g., `abc12345.apps.dynatrace.com`)
- **Authentication**: Uses OAuth2 Bearer token. Your OAuth2 client must have `app-engine:apps:run` scope. Does NOT use `DTIAM_ENVIRONMENT_TOKEN`.

**Examples:**

```bash
# List all apps in an environment
dtiam get apps -e abc12345

# Get app IDs for policy statements
dtiam get apps -e abc12345 --ids

# Get specific app details
dtiam get apps my-app-id -e abc12345

# Using environment variable
export DTIAM_ENVIRONMENT_URL=abc12345.apps.dynatrace.com
dtiam get apps
```

### get schemas

List or get Settings 2.0 schemas from the Environment API.

```bash
dtiam get schemas [IDENTIFIER] [OPTIONS]
```

| Argument/Option   | Short | Description                                     |
| ----------------- | ----- | ----------------------------------------------- |
| `IDENTIFIER`      |       | Schema ID or display name (optional)            |
| `--name`          | `-n`  | Filter by name (partial match on ID or name)    |
| `--environment`   | `-e`  | Environment ID or URL (required)                |
| `--ids`           |       | Output only schema IDs (for use in boundaries)  |
| `--builtin`       |       | Show only builtin schemas                       |
| `--search`        | `-s`  | Alias for `--name` (backward compatibility)     |
| `--output`        | `-o`  | Output format                                   |

Aliases: `get schema`

**Notes:**
- Requires an environment URL via `--environment` or `DTIAM_ENVIRONMENT_URL`
- Requires an environment API token via `DTIAM_ENVIRONMENT_TOKEN` with `settings.read` scope
- Schema IDs can be used in boundary conditions: `settings:schemaId = "builtin:alerting.profile";`
- Environment can be specified as ID (e.g., `abc12345`) or full URL (e.g., `abc12345.live.dynatrace.com`)

**Examples:**

```bash
# List all schemas in an environment
dtiam get schemas -e abc12345.live.dynatrace.com

# Get only builtin schema IDs
dtiam get schemas -e abc12345 --ids --builtin

# Search for alerting-related schemas
dtiam get schemas -e abc12345 --search alerting

# Get specific schema details
dtiam get schemas builtin:alerting.profile -e abc12345
```

### get service-users

List or get IAM service users (OAuth clients).

```bash
dtiam get service-users [IDENTIFIER] [OPTIONS]
```

| Argument/Option | Short | Description                              |
| --------------- | ----- | ---------------------------------------- |
| `IDENTIFIER`    |       | Service user UUID or name (optional)     |
| `--name`        | `-n`  | Filter by name (partial match)           |
| `--output`      | `-o`  | Output format                            |

**Examples:**

```bash
# List all service users
dtiam get service-users

# Filter service users by name
dtiam get service-users --name pipeline

# Get specific service user details
dtiam get service-users my-service-user
```

Aliases: `get service-user`

---

## describe

Show detailed resource information.

### describe group

Show detailed information about an IAM group.

```bash
dtiam describe group IDENTIFIER [--output FORMAT]
```

Displays: UUID, name, description, member count, members list, policy bindings.

### describe user

Show detailed information about an IAM user.

```bash
dtiam describe user IDENTIFIER [--output FORMAT]
```

Displays: UID, email, status, creation date, group memberships.

### describe policy

Show detailed information about an IAM policy.

```bash
dtiam describe policy IDENTIFIER [OPTIONS]
```

| Option     | Short | Description                             |
| ---------- | ----- | --------------------------------------- |
| `--level`  | `-l`  | Policy level: account (default), global |
| `--output` | `-o`  | Output format                           |

Displays: UUID, name, description, statement query, parsed permissions.

### describe environment

Show detailed information about a Dynatrace environment.

```bash
dtiam describe environment IDENTIFIER [--output FORMAT]
```

Aliases: `describe env`

### describe boundary

Show detailed information about an IAM policy boundary.

```bash
dtiam describe boundary IDENTIFIER [--output FORMAT]
```

Displays: UUID, name, description, boundary query, attached policies count.

---

## create

Create IAM resources.

### create group

Create a new IAM group.

```bash
dtiam create group [OPTIONS]
```

| Option          | Short | Description           |
| --------------- | ----- | --------------------- |
| `--name`        | `-n`  | Group name (required) |
| `--description` | `-d`  | Group description     |
| `--output`      | `-o`  | Output format         |

**Example:**

```bash
dtiam create group --name "LOB5" --description "LOB5 team"
```

### create policy

Create a new IAM policy.

```bash
dtiam create policy [OPTIONS]
```

| Option          | Short | Description                              |
| --------------- | ----- | ---------------------------------------- |
| `--name`        | `-n`  | Policy name (required)                   |
| `--statement`   | `-s`  | Policy statement query (required)        |
| `--description` | `-d`  | Policy description                       |
| `--level`       | `-l`  | Policy level (account only for creation) |
| `--output`      | `-o`  | Output format                            |

**Example:**

```bash
dtiam create policy --name "viewer" --statement "ALLOW settings:objects:read;"
```

### create binding

Create a policy binding (bind a policy to a group).

```bash
dtiam create binding [OPTIONS]
```

| Option       | Short | Description                      |
| ------------ | ----- | -------------------------------- |
| `--group`    | `-g`  | Group UUID or name (required)    |
| `--policy`   | `-p`  | Policy UUID or name (required)   |
| `--boundary` | `-b`  | Boundary UUID or name (optional) |
| `--output`   | `-o`  | Output format                    |

**Example:**

```bash
dtiam create binding --group "LOB5" --policy "admin-policy"
```

### create boundary

Create a new IAM policy boundary.

```bash
dtiam create boundary [OPTIONS]
```

| Option          | Short | Description                        |
| --------------- | ----- | ---------------------------------- |
| `--name`        | `-n`  | Boundary name (required)           |
| `--zones`       | `-z`  | Management zones (comma-separated) |
| `--query`       | `-q`  | Custom boundary query              |
| `--description` | `-d`  | Boundary description               |
| `--output`      | `-o`  | Output format                      |

Either `--zones` or `--query` must be provided.

**Example:**

```bash
dtiam create boundary --name "prod-only" --zones "Production,Staging"
```

---

## delete

Delete IAM resources.

### delete group

Delete an IAM group.

```bash
dtiam delete group IDENTIFIER [--force]
```

| Option    | Short | Description       |
| --------- | ----- | ----------------- |
| `--force` | `-f`  | Skip confirmation |

### delete policy

Delete an IAM policy.

```bash
dtiam delete policy IDENTIFIER [OPTIONS]
```

| Option    | Short | Description            |
| --------- | ----- | ---------------------- |
| `--level` | `-l`  | Policy level (account) |
| `--force` | `-f`  | Skip confirmation      |

### delete binding

Delete a policy binding.

```bash
dtiam delete binding [OPTIONS]
```

| Option     | Short | Description            |
| ---------- | ----- | ---------------------- |
| `--group`  | `-g`  | Group UUID (required)  |
| `--policy` | `-p`  | Policy UUID (required) |
| `--force`  | `-f`  | Skip confirmation      |

### delete boundary

Delete an IAM policy boundary.

```bash
dtiam delete boundary IDENTIFIER [--force]
```

---

## user

User management operations.

### user create

Create a new user in the account.

```bash
dtiam user create [OPTIONS]
```

| Option         | Short | Description                          |
| -------------- | ----- | ------------------------------------ |
| `--email`      | `-e`  | User email address (required)        |
| `--first-name` | `-f`  | User's first name                    |
| `--last-name`  | `-l`  | User's last name                     |
| `--groups`     | `-g`  | Comma-separated group UUIDs or names |
| `--output`     | `-o`  | Output format                        |

**Examples:**

```bash
dtiam user create --email user@example.com
dtiam user create --email user@example.com --first-name John --last-name Doe
dtiam user create --email user@example.com --groups "LOB5,LOB6"
```

### user delete

Delete a user from the account.

```bash
dtiam user delete USER [--force]
```

| Argument/Option | Short | Description       |
| --------------- | ----- | ----------------- |
| `USER`          |       | User email or UID |
| `--force`       | `-f`  | Skip confirmation |

**Example:**

```bash
dtiam user delete user@example.com --force
```

### user add-to-group

Add a user to an IAM group.

```bash
dtiam user add-to-group [OPTIONS]
```

| Option    | Short | Description                   |
| --------- | ----- | ----------------------------- |
| `--user`  | `-u`  | User email address (required) |
| `--group` | `-g`  | Group UUID or name (required) |

**Example:**

```bash
dtiam user add-to-group --user admin@example.com --group "LOB5"
```

### user remove-from-group

Remove a user from an IAM group.

```bash
dtiam user remove-from-group [OPTIONS]
```

| Option    | Short | Description                   |
| --------- | ----- | ----------------------------- |
| `--user`  | `-u`  | User email or UID (required)  |
| `--group` | `-g`  | Group UUID or name (required) |
| `--force` | `-f`  | Skip confirmation             |

### user list-groups

List all groups a user belongs to.

```bash
dtiam user list-groups USER [--output FORMAT]
```

### user info

Show detailed information about a user.

```bash
dtiam user info USER [--output FORMAT]
```

### user replace-groups

Replace all group memberships for a user.

This removes the user from all current groups and adds them to the specified groups.

```bash
dtiam user replace-groups [OPTIONS]
```

| Option     | Short | Description                                     |
| ---------- | ----- | ----------------------------------------------- |
| `--user`   | `-u`  | User email address (required)                   |
| `--groups` | `-g`  | Comma-separated group UUIDs or names (required) |
| `--force`  | `-f`  | Skip confirmation                               |

**Example:**

```bash
dtiam user replace-groups --user user@example.com --groups "LOB5,LOB6"
```

### user bulk-remove-groups

Remove a user from multiple groups at once.

```bash
dtiam user bulk-remove-groups [OPTIONS]
```

| Option     | Short | Description                                     |
| ---------- | ----- | ----------------------------------------------- |
| `--user`   | `-u`  | User email address (required)                   |
| `--groups` | `-g`  | Comma-separated group UUIDs or names (required) |
| `--force`  | `-f`  | Skip confirmation                               |

**Example:**

```bash
dtiam user bulk-remove-groups --user user@example.com --groups "LOB5,LOB6"
```

### user bulk-add-groups

Add a user to multiple groups at once.

```bash
dtiam user bulk-add-groups [OPTIONS]
```

| Option     | Short | Description                                     |
| ---------- | ----- | ----------------------------------------------- |
| `--user`   | `-u`  | User email address (required)                   |
| `--groups` | `-g`  | Comma-separated group UUIDs or names (required) |

**Example:**

```bash
dtiam user bulk-add-groups --user user@example.com --groups "LOB5,LOB6"
```

---

## bulk

Bulk operations for multiple resources.

### bulk add-users-to-group

Add multiple users to a group from a file.

```bash
dtiam bulk add-users-to-group [OPTIONS]
```

| Option                | Short | Description                                            |
| --------------------- | ----- | ------------------------------------------------------ |
| `--file`              | `-f`  | File with user emails (JSON, YAML, or CSV) (required)  |
| `--group`             | `-g`  | Group UUID or name (required)                          |
| `--email-field`       | `-e`  | Field name containing email addresses (default: email) |
| `--continue-on-error` |       | Continue processing on errors                          |

**CSV Example:**

```csv
email
user1@example.com
user2@example.com
```

### bulk remove-users-from-group

Remove multiple users from a group from a file.

```bash
dtiam bulk remove-users-from-group [OPTIONS]
```

| Option                | Short | Description                                         |
| --------------------- | ----- | --------------------------------------------------- |
| `--file`              | `-f`  | File with user emails/UIDs (required)               |
| `--group`             | `-g`  | Group UUID or name (required)                       |
| `--user-field`        | `-u`  | Field name containing email or UID (default: email) |
| `--continue-on-error` |       | Continue processing on errors                       |
| `--force`             | `-F`  | Skip confirmation                                   |

### bulk create-groups

Create multiple groups from a file.

```bash
dtiam bulk create-groups [OPTIONS]
```

| Option                | Short | Description                                           |
| --------------------- | ----- | ----------------------------------------------------- |
| `--file`              | `-f`  | File with group definitions (JSON or YAML) (required) |
| `--continue-on-error` |       | Continue processing on errors                         |

**YAML Example:**

```yaml
- name: "Group A"
  description: "Description for Group A"
- name: "Group B"
  description: "Description for Group B"
```

### bulk create-groups-with-policies

Create groups with policies and bindings from a CSV file.

This command creates groups, boundaries, and policy bindings in one operation, matching the behavior from the 2.0 project.

```bash
dtiam bulk create-groups-with-policies [OPTIONS]
```

| Option                | Short | Description                                         |
| --------------------- | ----- | --------------------------------------------------- |
| `--file`              | `-f`  | CSV file with group, policy, and binding definitions (required) |
| `--continue-on-error` |       | Continue processing on errors                       |

**CSV Columns:**

| Column              | Required | Description                                          |
| ------------------- | -------- | ---------------------------------------------------- |
| `group_name`        | Yes      | Name of the group to create                          |
| `policy_name`       | Yes      | Policy to bind to the group                          |
| `level`             | No       | 'account' or 'environment' (default: account)        |
| `level_id`          | No       | Environment ID if level=environment                  |
| `management_zones`  | No       | Zone(s) for boundary (pipe-separated)                |
| `boundary_name`     | No       | Custom boundary name (default: {group}-Boundary)     |
| `description`       | No       | Group description                                    |

**CSV Example:**

```csv
group_name,policy_name,level,level_id,management_zones,boundary_name,description
LOB5,Standard User - Config,account,,,,LOB5 team - global read access (account level)
LOB5,Pro User,environment,abc12345,LOB5,LOB5-Boundary,LOB5 team - restricted write access (environment level)
LOB6,Standard User - Config,account,,,,LOB6 team - global read access (account level)
LOB6,Pro User,environment,abc12345,LOB6,LOB6-Boundary,LOB6 team - restricted write access (environment level)
```

**Example Usage:**

```bash
# Create groups with policies from CSV
dtiam bulk create-groups-with-policies --file examples/bulk/sample_bulk_groups.csv

# Dry-run mode to preview changes
dtiam --dry-run bulk create-groups-with-policies --file groups.csv

# Continue on errors
dtiam bulk create-groups-with-policies --file groups.csv --continue-on-error
```

**Notes:**
- Creates groups if they don't exist
- Creates boundaries with management zones if specified
- Creates policy bindings at account or environment level
- Skips existing resources (idempotent)
- See [examples/bulk/sample_bulk_groups.csv](../examples/bulk/sample_bulk_groups.csv) for a complete example

### bulk create-bindings

Create multiple policy bindings from a file.

```bash
dtiam bulk create-bindings [OPTIONS]
```

| Option                | Short | Description                                             |
| --------------------- | ----- | ------------------------------------------------------- |
| `--file`              | `-f`  | File with binding definitions (JSON or YAML) (required) |
| `--continue-on-error` |       | Continue processing on errors                           |

**YAML Example:**

```yaml
- group: "group-name"
  policy: "policy-name"
  boundary: "optional-boundary"
```

### bulk export-group-members

Export group members to a file.

```bash
dtiam bulk export-group-members [OPTIONS]
```

| Option     | Short | Description                                   |
| ---------- | ----- | --------------------------------------------- |
| `--group`  | `-g`  | Group UUID or name (required)                 |
| `--output` | `-o`  | Output file path                              |
| `--format` | `-f`  | Output format: csv, json, yaml (default: csv) |

---

## template

Template-based resource creation.

### template list

List all available templates.

```bash
dtiam template list [--output FORMAT]
```

### template show

Show a template definition and its required variables.

```bash
dtiam template show NAME [--output FORMAT]
```

### template render

Render a template with the given variables.

```bash
dtiam template render NAME [OPTIONS]
```

| Option       | Short | Description                               |
| ------------ | ----- | ----------------------------------------- |
| `--var`      | `-v`  | Variable in key=value format (repeatable) |
| `--var-file` | `-f`  | YAML/JSON file with variables             |
| `--output`   | `-o`  | Output format                             |

**Example:**

```bash
dtiam template render group-team --var team_name=LOB5 --var description="LOB5"
```

### template apply

Render a template and create the resource.

```bash
dtiam template apply NAME [OPTIONS]
```

| Option       | Short | Description                               |
| ------------ | ----- | ----------------------------------------- |
| `--var`      | `-v`  | Variable in key=value format (repeatable) |
| `--var-file` | `-f`  | YAML/JSON file with variables             |

**Example:**

```bash
dtiam template apply group-team --var team_name=LOB5
```

### template save

Save a custom template.

```bash
dtiam template save NAME [OPTIONS]
```

| Option          | Short | Description                                                |
| --------------- | ----- | ---------------------------------------------------------- |
| `--kind`        | `-k`  | Resource kind: Group, Policy, Boundary, Binding (required) |
| `--file`        | `-f`  | YAML/JSON file with template definition (required)         |
| `--description` | `-d`  | Template description                                       |

### template delete

Delete a custom template.

```bash
dtiam template delete NAME [--force]
```

### template path

Show the path where custom templates are stored.

```bash
dtiam template path
```

---

## zones

> **DEPRECATION NOTICE:** Management Zone features are provided for legacy purposes only and will be removed in a future release.

Management zone operations.

### zones list

List management zones.

```bash
dtiam zones list [OPTIONS]
```

| Option     | Short | Description    |
| ---------- | ----- | -------------- |
| `--name`   | `-n`  | Filter by name |
| `--output` | `-o`  | Output format  |

### zones get

Get a management zone by ID or name.

```bash
dtiam zones get IDENTIFIER [--output FORMAT]
```

### zones export

Export management zones to a file.

```bash
dtiam zones export [OPTIONS]
```

| Option     | Short | Description                                    |
| ---------- | ----- | ---------------------------------------------- |
| `--output` | `-o`  | Output file path                               |
| `--format` | `-f`  | Output format: yaml, json, csv (default: yaml) |

### zones compare-groups

Compare zone names with group names to find matches.

```bash
dtiam zones compare-groups [OPTIONS]
```

| Option             | Short | Description                 |
| ------------------ | ----- | --------------------------- |
| `--case-sensitive` | `-c`  | Use case-sensitive matching |
| `--output`         | `-o`  | Output format               |

---

## analyze

Analyze permissions and policies.

### analyze user-permissions

Calculate effective permissions for a user.

```bash
dtiam analyze user-permissions USER [OPTIONS]
```

| Option     | Short | Description    |
| ---------- | ----- | -------------- |
| `--output` | `-o`  | Output format  |
| `--export` | `-e`  | Export to file |

**Example:**

```bash
dtiam analyze user-permissions admin@example.com -o json
```

### analyze group-permissions

Calculate effective permissions for a group.

```bash
dtiam analyze group-permissions GROUP [OPTIONS]
```

| Option     | Short | Description    |
| ---------- | ----- | -------------- |
| `--output` | `-o`  | Output format  |
| `--export` | `-e`  | Export to file |

### analyze permissions-matrix

Generate a permissions matrix.

```bash
dtiam analyze permissions-matrix [OPTIONS]
```

| Option     | Short | Description                                   |
| ---------- | ----- | --------------------------------------------- |
| `--scope`  | `-s`  | Scope: policies or groups (default: policies) |
| `--output` | `-o`  | Output format                                 |
| `--export` | `-e`  | Export to CSV file                            |

### analyze policy

Analyze a policy's permissions and bindings.

```bash
dtiam analyze policy IDENTIFIER [--output FORMAT]
```

Shows: parsed permissions, bound groups, boundary restrictions.

### analyze least-privilege

Analyze policies for least-privilege compliance.

```bash
dtiam analyze least-privilege [OPTIONS]
```

| Option     | Short | Description             |
| ---------- | ----- | ----------------------- |
| `--output` | `-o`  | Output format           |
| `--export` | `-e`  | Export findings to file |

Identifies policies with:

- Wildcard permissions
- Resource wildcards
- Write/manage/delete/admin access
- No conditions (unrestricted)

### analyze effective-user

Get effective permissions for a user via the Dynatrace API.

This calls the Dynatrace resolution API directly to get permissions as computed by the platform, which is the authoritative source.

```bash
dtiam analyze effective-user USER [OPTIONS]
```

| Option       | Short | Description                                                 |
| ------------ | ----- | ----------------------------------------------------------- |
| `--level`    | `-l`  | Level type: account, environment, global (default: account) |
| `--level-id` |       | Level ID (uses account UUID if not specified)               |
| `--services` | `-s`  | Comma-separated service filter                              |
| `--output`   | `-o`  | Output format                                               |
| `--export`   | `-e`  | Export to file                                              |

**Examples:**

```bash
dtiam analyze effective-user admin@example.com
dtiam analyze effective-user admin@example.com --level environment --level-id env123
dtiam analyze effective-user admin@example.com --services settings,entities
```

### analyze effective-group

Get effective permissions for a group via the Dynatrace API.

This calls the Dynatrace resolution API directly to get permissions as computed by the platform, which is the authoritative source.

```bash
dtiam analyze effective-group GROUP [OPTIONS]
```

| Option       | Short | Description                                                 |
| ------------ | ----- | ----------------------------------------------------------- |
| `--level`    | `-l`  | Level type: account, environment, global (default: account) |
| `--level-id` |       | Level ID (uses account UUID if not specified)               |
| `--services` | `-s`  | Comma-separated service filter                              |
| `--output`   | `-o`  | Output format                                               |
| `--export`   | `-e`  | Export to file                                              |

**Examples:**

```bash
dtiam analyze effective-group "LOB5"
dtiam analyze effective-group "LOB5" -o json --export perms.json
```

---

## export

Export resources and data.

### export all

Export all IAM resources to files.

```bash
dtiam export all [OPTIONS]
```

| Option                               | Short | Description                                    |
| ------------------------------------ | ----- | ---------------------------------------------- |
| `--output`                           | `-o`  | Output directory (default: .)                  |
| `--format`                           | `-f`  | Output format: csv, json, yaml (default: csv)  |
| `--prefix`                           | `-p`  | File name prefix (default: dtiam)              |
| `--include`                          | `-i`  | Comma-separated list of exports to include     |
| `--detailed`                         | `-d`  | Include detailed/enriched data                 |
| `--timestamp-dir/--no-timestamp-dir` |       | Create timestamped subdirectory (default: yes) |

Available exports: environments, groups, users, policies, bindings, boundaries

**Example:**

```bash
dtiam export all -o ./backup -f json --detailed
dtiam export all --include groups,policies
```

### export group

Export a single group with its details.

```bash
dtiam export group IDENTIFIER [OPTIONS]
```

| Option                             | Short | Description                               |
| ---------------------------------- | ----- | ----------------------------------------- |
| `--output`                         | `-o`  | Output file                               |
| `--format`                         | `-f`  | Output format: yaml, json (default: yaml) |
| `--include-members/--no-members`   |       | Include member list (default: yes)        |
| `--include-policies/--no-policies` |       | Include policy bindings (default: yes)    |

### export policy

Export a single policy with its details.

```bash
dtiam export policy IDENTIFIER [OPTIONS]
```

| Option          | Short | Description                               |
| --------------- | ----- | ----------------------------------------- |
| `--output`      | `-o`  | Output file                               |
| `--format`      | `-f`  | Output format: yaml, json (default: yaml) |
| `--as-template` | `-t`  | Export as reusable template               |

---

## group

Advanced group operations.

### group clone

Clone an existing group with its configuration.

```bash
dtiam group clone SOURCE [OPTIONS]
```

| Argument/Option                    | Short | Description                               |
| ---------------------------------- | ----- | ----------------------------------------- |
| `SOURCE`                           |       | Source group UUID or name                 |
| `--name`                           | `-n`  | Name for the cloned group (required)      |
| `--description`                    | `-d`  | Description (uses source if not provided) |
| `--include-members`                | `-m`  | Copy members to new group                 |
| `--include-policies/--no-policies` |       | Copy policy bindings (default: yes)       |
| `--output`                         | `-o`  | Output format                             |

**Example:**

```bash
dtiam group clone "Source Group" --name "New Group" --include-members
```

### group setup

Create a group with policy binding in one command.

```bash
dtiam group setup [OPTIONS]
```

| Option          | Short | Description                            |
| --------------- | ----- | -------------------------------------- |
| `--name`        | `-n`  | Group name (required)                  |
| `--policy`      | `-p`  | Policy UUID or name to bind (required) |
| `--boundary`    | `-b`  | Boundary UUID or name (optional)       |
| `--description` | `-d`  | Group description                      |
| `--output`      | `-o`  | Output format                          |

**Example:**

```bash
dtiam group setup --name "LOB5" --policy "devops-policy" --boundary "prod-boundary"
```

### group list-bindings

List all policy bindings for a group.

```bash
dtiam group list-bindings GROUP [--output FORMAT]
```

### group list-members

List all members of a group.

```bash
dtiam group list-members GROUP [--output FORMAT]
```

---

## boundary

Boundary attach/detach operations.

### boundary attach

Attach a boundary to an existing binding.

```bash
dtiam boundary attach [OPTIONS]
```

| Option       | Short | Description                      |
| ------------ | ----- | -------------------------------- |
| `--group`    | `-g`  | Group UUID or name (required)    |
| `--policy`   | `-p`  | Policy UUID or name (required)   |
| `--boundary` | `-b`  | Boundary UUID or name (required) |

**Example:**

```bash
dtiam boundary attach --group "LOB5" --policy "admin-policy" --boundary "prod-boundary"
```

### boundary detach

Detach a boundary from a binding.

```bash
dtiam boundary detach [OPTIONS]
```

| Option       | Short | Description                      |
| ------------ | ----- | -------------------------------- |
| `--group`    | `-g`  | Group UUID or name (required)    |
| `--policy`   | `-p`  | Policy UUID or name (required)   |
| `--boundary` | `-b`  | Boundary UUID or name (required) |
| `--force`    | `-f`  | Skip confirmation                |

### boundary list-attached

List all bindings that use a boundary.

```bash
dtiam boundary list-attached BOUNDARY [--output FORMAT]
```

### boundary create-app-boundary

Create a boundary restricting access to specific apps using `shared:app-id` conditions.

```bash
dtiam boundary create-app-boundary NAME [OPTIONS]
```

| Option              | Short | Description                                          |
| ------------------- | ----- | ---------------------------------------------------- |
| `--app-id`          | `-a`  | App ID to include (repeatable)                       |
| `--file`            | `-f`  | File with app IDs (one per line)                     |
| `--not-in`          |       | Use NOT IN instead of IN (exclude apps)              |
| `--environment`     | `-e`  | Environment URL for app validation                   |
| `--description`     | `-d`  | Boundary description                                 |
| `--skip-validation` |       | Skip app ID validation against registry              |
| `--output`          | `-o`  | Output format                                        |

**Examples:**

```bash
# Create boundary allowing specific apps
dtiam boundary create-app-boundary "DashboardAccess" \
  --app-id "dynatrace.dashboards" \
  --app-id "dynatrace.notebooks" \
  -e "abc12345.apps.dynatrace.com"

# Create boundary excluding specific apps (NOT IN)
dtiam boundary create-app-boundary "NoLegacyApps" \
  --app-id "dynatrace.classic.smartscape" \
  --not-in \
  -e "abc12345.apps.dynatrace.com"

# Load app IDs from file
dtiam boundary create-app-boundary "FromFile" \
  --file app-ids.txt \
  -e "abc12345.apps.dynatrace.com"

# Skip validation (use with caution)
dtiam boundary create-app-boundary "Custom" \
  --app-id "custom.app.id" \
  --skip-validation
```

The generated boundary query format:
- **IN**: `shared:app-id IN ("app1", "app2");`
- **NOT IN**: `shared:app-id NOT IN ("app1", "app2");`

### boundary create-schema-boundary

Create a boundary restricting access to specific settings schemas using `settings:schemaId` conditions.

```bash
dtiam boundary create-schema-boundary NAME [OPTIONS]
```

| Option              | Short | Description                                          |
| ------------------- | ----- | ---------------------------------------------------- |
| `--schema-id`       | `-s`  | Schema ID to include (repeatable)                    |
| `--file`            | `-f`  | File with schema IDs (one per line)                  |
| `--not-in`          |       | Use NOT IN instead of IN (exclude schemas)           |
| `--environment`     | `-e`  | Environment URL for schema validation                |
| `--description`     | `-d`  | Boundary description                                 |
| `--skip-validation` |       | Skip schema ID validation against environment        |
| `--output`          | `-o`  | Output format                                        |

**Examples:**

```bash
# Allow access to specific schemas only
dtiam boundary create-schema-boundary "AlertingOnly" \
  --schema-id "builtin:alerting.profile" \
  --schema-id "builtin:alerting.maintenance-window" \
  -e "abc12345.live.dynatrace.com"

# Exclude specific schemas (NOT IN)
dtiam boundary create-schema-boundary "NoSpanSettings" \
  --schema-id "builtin:span-attribute" \
  --schema-id "builtin:span-capture-rule" \
  --not-in \
  -e "abc12345.live.dynatrace.com"

# Load schema IDs from file
dtiam boundary create-schema-boundary "FromFile" \
  --file schema-ids.txt \
  -e "abc12345.live.dynatrace.com"
```

The generated boundary query format:
- **IN**: `settings:schemaId IN ("builtin:alerting.profile", "builtin:span-attribute");`
- **NOT IN**: `settings:schemaId NOT IN ("builtin:span-attribute");`

---

## cache

Cache management.

### cache stats

Show cache statistics.

```bash
dtiam cache stats
```

Displays: active entries, expired entries, total entries, hits, misses, hit rate, default TTL.

### cache clear

Clear cache entries.

```bash
dtiam cache clear [OPTIONS]
```

| Option           | Short | Description                         |
| ---------------- | ----- | ----------------------------------- |
| `--force`        | `-f`  | Skip confirmation                   |
| `--expired-only` | `-e`  | Only clear expired entries          |
| `--prefix`       | `-p`  | Only clear entries with this prefix |

**Examples:**

```bash
dtiam cache clear                    # Clear all entries
dtiam cache clear --expired-only     # Clear only expired entries
dtiam cache clear --prefix groups    # Clear entries starting with 'groups'
```

### cache keys

List cache keys.

```bash
dtiam cache keys [OPTIONS]
```

| Option     | Short | Description                        |
| ---------- | ----- | ---------------------------------- |
| `--prefix` | `-p`  | Filter by prefix                   |
| `--limit`  | `-n`  | Maximum keys to show (default: 50) |

### cache reset-stats

Reset cache hit/miss statistics.

```bash
dtiam cache reset-stats
```

### cache set-ttl

Set the default cache TTL.

```bash
dtiam cache set-ttl SECONDS
```

| Argument  | Description            |
| --------- | ---------------------- |
| `SECONDS` | Default TTL in seconds |

---

## service-user

Service user (OAuth client) management.

Service users are used for programmatic API access. When you create a service user, you receive OAuth client credentials that can be used to authenticate API requests.

### service-user list

List all service users in the account.

```bash
dtiam service-user list [--output FORMAT]
```

### service-user get

Get details of a service user.

```bash
dtiam service-user get USER [--output FORMAT]
```

| Argument | Description               |
| -------- | ------------------------- |
| `USER`   | Service user UUID or name |

### service-user create

Create a new service user (OAuth client).

**IMPORTANT:** Save the client secret immediately - it cannot be retrieved later!

```bash
dtiam service-user create [OPTIONS]
```

| Option               | Short | Description                          |
| -------------------- | ----- | ------------------------------------ |
| `--name`             | `-n`  | Service user name (required)         |
| `--description`      | `-d`  | Description                          |
| `--groups`           | `-g`  | Comma-separated group UUIDs or names |
| `--save-credentials` | `-s`  | Save credentials to JSON file        |
| `--output`           | `-o`  | Output format                        |

**Examples:**

```bash
dtiam service-user create --name "CI Pipeline"
dtiam service-user create --name "CI Pipeline" --groups "LOB5,LOB6"
dtiam service-user create --name "CI Pipeline" --save-credentials creds.json
```

### service-user update

Update a service user.

```bash
dtiam service-user update USER [OPTIONS]
```

| Argument/Option | Short | Description               |
| --------------- | ----- | ------------------------- |
| `USER`          |       | Service user UUID or name |
| `--name`        | `-n`  | New name                  |
| `--description` | `-d`  | New description           |
| `--output`      | `-o`  | Output format             |

**Example:**

```bash
dtiam service-user update my-service-user --name "New Name"
```

### service-user delete

Delete a service user.

```bash
dtiam service-user delete USER [--force]
```

| Argument/Option | Short | Description               |
| --------------- | ----- | ------------------------- |
| `USER`          |       | Service user UUID or name |
| `--force`       | `-f`  | Skip confirmation         |

**Warning:** Deleting a service user will invalidate any OAuth tokens issued to it.

### service-user add-to-group

Add a service user to a group.

```bash
dtiam service-user add-to-group [OPTIONS]
```

| Option    | Short | Description                          |
| --------- | ----- | ------------------------------------ |
| `--user`  | `-u`  | Service user UUID or name (required) |
| `--group` | `-g`  | Group UUID or name (required)        |

**Example:**

```bash
dtiam service-user add-to-group --user my-service-user --group LOB5
```

### service-user remove-from-group

Remove a service user from a group.

```bash
dtiam service-user remove-from-group [OPTIONS]
```

| Option    | Short | Description                          |
| --------- | ----- | ------------------------------------ |
| `--user`  | `-u`  | Service user UUID or name (required) |
| `--group` | `-g`  | Group UUID or name (required)        |
| `--force` | `-f`  | Skip confirmation                    |

### service-user list-groups

List all groups a service user belongs to.

```bash
dtiam service-user list-groups USER [--output FORMAT]
```

| Argument | Description               |
| -------- | ------------------------- |
| `USER`   | Service user UUID or name |

---

## account

Account limits and subscription information.

### account limits

List account limits and quotas.

```bash
dtiam account limits [--output FORMAT]
```

Shows current usage and maximum allowed values for account resources like users, groups, and environments. Includes status indicators for limits approaching or at capacity.

**Example:**

```bash
dtiam account limits
dtiam account limits -o json
```

### account check-capacity

Check if there's capacity for additional resources.

```bash
dtiam account check-capacity LIMIT [OPTIONS]
```

| Argument/Option | Short | Description                             |
| --------------- | ----- | --------------------------------------- |
| `LIMIT`         |       | Limit name (e.g., maxUsers, maxGroups)  |
| `--count`       | `-n`  | Number of resources to add (default: 1) |
| `--output`      | `-o`  | Output format                           |

**Examples:**

```bash
dtiam account check-capacity maxUsers
dtiam account check-capacity maxGroups --count 5
```

### account subscriptions

List account subscriptions.

```bash
dtiam account subscriptions [--output FORMAT]
```

Shows all subscriptions including type, status, and time period.

### account subscription

Get details of a specific subscription.

```bash
dtiam account subscription SUBSCRIPTION [--output FORMAT]
```

| Argument       | Description               |
| -------------- | ------------------------- |
| `SUBSCRIPTION` | Subscription UUID or name |

### account forecast

Get usage forecast for subscriptions.

```bash
dtiam account forecast [SUBSCRIPTION] [--output FORMAT]
```

| Argument       | Description                |
| -------------- | -------------------------- |
| `SUBSCRIPTION` | Optional subscription UUID |

### account capabilities

List subscription capabilities.

```bash
dtiam account capabilities [SUBSCRIPTION] [--output FORMAT]
```

| Argument       | Description                |
| -------------- | -------------------------- |
| `SUBSCRIPTION` | Optional subscription UUID |

---

## Exit Codes

| Code | Description                                         |
| ---- | --------------------------------------------------- |
| 0    | Success                                             |
| 1    | Error (resource not found, permission denied, etc.) |

## See Also

- [Quick Start Guide](QUICK_START.md)
- [Architecture](ARCHITECTURE.md)
- [API Reference](API_REFERENCE.md)
