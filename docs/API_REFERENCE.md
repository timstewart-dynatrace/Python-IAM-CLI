# API Reference

> **DISCLAIMER:** This tool is provided "as-is" without warranty. Use at your own risk. This is an independent, community-developed tool and is **NOT produced, endorsed, or supported by Dynatrace**.

Programmatic usage guide for dtiam modules.

## Overview

While dtiam is primarily a CLI tool, its modules can be used programmatically for scripting and automation.

## Configuration

### Loading Configuration

```python
from dtiam.config import load_config, save_config, Config

# Load existing configuration
config = load_config()

# Access current context
context = config.get_current_context()
print(f"Account UUID: {context.account_uuid}")

# Get specific context
prod_context = config.get_context("production")

# Get credential
credential = config.get_credential("prod-creds")
print(f"Client ID: {credential.client_id}")
```

### Creating Configuration Programmatically

```python
from dtiam.config import Config, save_config

config = Config()

# Add credentials
config.set_credential(
    name="prod-creds",
    client_id="dt0s01.XXXX",
    client_secret="dt0s01.XXXX.YYYY"
)

# Add context
config.set_context(
    name="production",
    account_uuid="abc-123-def",
    credentials_ref="prod-creds"
)

# Set as current context
config.current_context = "production"

# Save to file
save_config(config)
```

### Environment Variables

```python
from dtiam.config import get_env_override

# Check for environment overrides
context = get_env_override("context")  # DTIAM_CONTEXT
client_id = get_env_override("client_id")  # DTIAM_CLIENT_ID
```

## HTTP Client

### Creating a Client

```python
from dtiam.config import load_config
from dtiam.client import create_client_from_config, Client

# From configuration file
config = load_config()
client = create_client_from_config(config, context_name="production", verbose=True)

# Use the client
try:
    response = client.get("/groups")
    groups = response.json()
finally:
    client.close()

# Context manager usage
with create_client_from_config(config) as client:
    response = client.get("/groups")
    groups = response.json()
```

### Direct Client Construction

```python
from dtiam.client import Client, RetryConfig
from dtiam.utils.auth import TokenManager

# Create token manager
token_manager = TokenManager(
    client_id="dt0s01.XXXX",
    client_secret="dt0s01.XXXX.YYYY",
    account_uuid="abc-123-def"
)

# Custom retry configuration
retry_config = RetryConfig(
    max_retries=5,
    retry_statuses=[429, 500, 502, 503, 504],
    initial_delay=0.5,
    max_delay=30.0,
    exponential_base=2.0
)

# Create client
client = Client(
    account_uuid="abc-123-def",
    token_manager=token_manager,
    timeout=60.0,
    retry_config=retry_config,
    verbose=True
)

# Make requests
response = client.get("/groups")
response = client.post("/groups", json={"name": "New Group"})
response = client.put("/groups/uuid", json={"name": "Updated"})
response = client.delete("/groups/uuid")
```

### Error Handling

```python
from dtiam.client import APIError

try:
    response = client.get("/groups/invalid-uuid")
except APIError as e:
    print(f"Status: {e.status_code}")
    print(f"Message: {e}")
    print(f"Body: {e.response_body}")
```

## Resource Handlers

### Groups

```python
from dtiam.resources.groups import GroupHandler

handler = GroupHandler(client)

# List all groups
groups = handler.list()

# Get by UUID
group = handler.get("uuid-here")

# Get by name
group = handler.get_by_name("LOB5")

# Get expanded (includes members and policies)
expanded = handler.get_expanded("uuid-here")

# Create a group
new_group = handler.create(
    name="New Team",
    description="A new team",
)

# Update a group
updated = handler.update("uuid-here", {
    "name": "Updated Name",
    "description": "Updated description"
})

# Delete a group
success = handler.delete("uuid-here")

# Member operations
members = handler.get_members("group-uuid")
handler.add_member("group-uuid", "user@example.com")
handler.remove_member("group-uuid", "user-uid")

# Clone a group
cloned = handler.clone(
    source_group_id="source-uuid",
    new_name="Cloned Group",
    new_description="A clone",
    include_members=True,
    include_policies=True
)

# Setup with policy binding
result = handler.setup_with_policy(
    group_name="New Team",
    policy_uuid="policy-uuid",
    boundary_uuid="boundary-uuid",  # optional
    description="Team description"
)
```

### Users

```python
from dtiam.resources.users import UserHandler

handler = UserHandler(client)

# List all users
users = handler.list()

# List including service users
users = handler.list(include_service_users=True)

# Get by UID
user = handler.get("user-uid")

# Get by email
user = handler.get_by_email("user@example.com")

# Get expanded (includes groups)
expanded = handler.get_expanded("user-uid")

# Get user's groups
groups = handler.get_groups("user-uid")

# Create a user
new_user = handler.create(
    email="user@example.com",
    first_name="John",
    last_name="Doe",
    groups=["group-uuid-1", "group-uuid-2"]  # optional
)

# Delete a user
success = handler.delete("user-uid")
```

### Service Users

```python
from dtiam.resources.service_users import ServiceUserHandler

handler = ServiceUserHandler(client)

# List all service users
service_users = handler.list()

# Get by UUID
user = handler.get("service-user-uuid")

# Get by name
user = handler.get_by_name("CI Pipeline")

# Get expanded (includes groups)
expanded = handler.get_expanded("service-user-uuid")

# Create a service user (returns client credentials!)
result = handler.create(
    name="CI Pipeline",
    description="CI/CD automation",
    groups=["group-uuid-1", "group-uuid-2"]  # optional
)
# IMPORTANT: Save result["clientId"] and result["clientSecret"]
# The secret cannot be retrieved later!

# Update a service user
updated = handler.update(
    "service-user-uuid",
    name="New Name",
    description="Updated description"
)

# Delete a service user
success = handler.delete("service-user-uuid")

# Group management
groups = handler.get_groups("service-user-uuid")
handler.add_to_group("service-user-uuid", "group-uuid")
handler.remove_from_group("service-user-uuid", "group-uuid")
```

### Policies

```python
from dtiam.resources.policies import PolicyHandler

# Account-level policies
handler = PolicyHandler(
    client,
    level_type="account",
    level_id=client.account_uuid
)

# Global policies (read-only)
global_handler = PolicyHandler(
    client,
    level_type="global",
    level_id="global"
)

# List policies
policies = handler.list()

# Get by UUID
policy = handler.get("policy-uuid")

# Get by name
policy = handler.get_by_name("admin-policy")

# Create a policy
new_policy = handler.create(
    name="viewer-policy",
    statement_query="ALLOW settings:objects:read;",
    description="Read-only access",
)

# Update a policy
updated = handler.update("policy-uuid", {
    "name": "updated-policy",
    "statementQuery": "ALLOW settings:objects:read; ALLOW settings:schemas:read;"
})

# Delete a policy
success = handler.delete("policy-uuid")
```

### Bindings

```python
from dtiam.resources.bindings import BindingHandler

handler = BindingHandler(
    client,
    level_type="account",
    level_id=client.account_uuid
)

# List all bindings
bindings = handler.list()

# Get bindings for a group
group_bindings = handler.get_for_group("group-uuid")

# Create a binding
binding = handler.create(
    group_uuid="group-uuid",
    policy_uuid="policy-uuid",
    boundaries=["boundary-uuid"]  # optional
)

# Delete a binding
success = handler.delete(
    group_uuid="group-uuid",
    policy_uuid="policy-uuid"
)

# Add boundary to existing binding
handler.add_boundary("group-uuid", "policy-uuid", "boundary-uuid")

# Remove boundary from binding
handler.remove_boundary("group-uuid", "policy-uuid", "boundary-uuid")
```

### Boundaries

```python
from dtiam.resources.boundaries import BoundaryHandler

handler = BoundaryHandler(client)

# List boundaries
boundaries = handler.list()

# Get by UUID
boundary = handler.get("boundary-uuid")

# Get by name
boundary = handler.get_by_name("prod-boundary")

# Create from management zones
boundary = handler.create_from_zones(
    name="Production Only",
    management_zones=["Production", "Staging"],
    description="Restricts to production zones"
)

# Create with custom query
boundary = handler.create(
    name="Custom Boundary",
    boundary_query="environment.tag.equals('production')",
    description="Custom boundary query",
)

# Get attached policies
attached = handler.get_attached_policies("boundary-uuid")

# Delete a boundary
success = handler.delete("boundary-uuid")
```

### Environments

```python
from dtiam.resources.environments import EnvironmentHandler

handler = EnvironmentHandler(client)

# List environments
environments = handler.list()

# Get by ID
env = handler.get("env-id")

# Get by name
env = handler.get_by_name("Production")
```

### Account Limits

```python
from dtiam.resources.limits import AccountLimitsHandler

handler = AccountLimitsHandler(client)

# List all limits
limits = handler.list()

# Get a specific limit
limit = handler.get("maxUsers")

# Get summary with usage percentages
summary = handler.get_summary()
# {
#     "limits": [
#         {"name": "maxUsers", "current": 50, "max": 100, "usage_percent": 50.0, "status": "ok"},
#         {"name": "maxGroups", "current": 85, "max": 100, "usage_percent": 85.0, "status": "near_capacity"},
#     ],
#     "total_limits": 5,
#     "limits_near_capacity": 1,
#     "limits_at_capacity": 0,
# }

# Check capacity before adding resources
result = handler.check_capacity("maxUsers", additional=10)
# {
#     "limit_name": "maxUsers",
#     "has_capacity": True,
#     "current": 50,
#     "max": 100,
#     "available": 50,
#     "message": "Capacity available (50 remaining)"
# }
```

### Subscriptions

```python
from dtiam.resources.subscriptions import SubscriptionHandler

handler = SubscriptionHandler(client)

# List all subscriptions
subscriptions = handler.list()

# Get a specific subscription
sub = handler.get("subscription-uuid")

# Get by name
sub = handler.get_by_name("My Subscription")

# Get summary
summary = handler.get_summary()
# {
#     "total_subscriptions": 2,
#     "active_subscriptions": 2,
#     "subscriptions": [...]
# }

# Get usage forecast
forecast = handler.get_forecast()
forecast = handler.get_forecast("subscription-uuid")  # specific subscription

# Get usage for a subscription
usage = handler.get_usage("subscription-uuid")

# Get capabilities
capabilities = handler.get_capabilities()
capabilities = handler.get_capabilities("subscription-uuid")
```

### Management Zones (Legacy)

> **DEPRECATION NOTICE:** Management Zone features are provided for legacy purposes only and will be removed in a future release.

```python
from dtiam.resources.zones import ZoneHandler

handler = ZoneHandler(client)

# List zones
zones = handler.list()

# Get by ID
zone = handler.get("zone-id")

# Get by name
zone = handler.get_by_name("Production Zone")

# Compare zones with groups
from dtiam.resources.groups import GroupHandler
group_handler = GroupHandler(client)
groups = group_handler.list()

comparison = handler.compare_with_groups(groups, case_sensitive=False)
# Returns: matched, unmatched_zones, unmatched_groups
```

## Output Formatting

### Using the Printer

```python
from dtiam.output import Printer, OutputFormat, Column

# Create printer
printer = Printer(format=OutputFormat.TABLE, plain=False)

# Print data
data = [{"uuid": "123", "name": "Test"}]
printer.print(data)

# With custom columns
columns = [
    Column("uuid", "UUID"),
    Column("name", "NAME"),
    Column("description", "DESCRIPTION", wide_only=True),
]
printer.print(data, columns)

# Get as string instead of printing
output_str = printer.format_str(data, columns)
```

### Output Formats

```python
from dtiam.output import OutputFormat

# Available formats
OutputFormat.TABLE   # ASCII table (default)
OutputFormat.WIDE    # Table with extra columns
OutputFormat.JSON    # JSON output
OutputFormat.YAML    # YAML output
OutputFormat.CSV     # CSV output
OutputFormat.PLAIN   # Machine-readable JSON
```

### Custom Columns

```python
from dtiam.output import Column

# Basic column
col = Column("name", "NAME")

# Wide-only column (hidden in normal table view)
col = Column("createdAt", "CREATED", wide_only=True)

# With custom formatter
col = Column(
    "status",
    "STATUS",
    formatter=lambda x: "Active" if x == "ACTIVE" else "Inactive"
)

# Nested key access
col = Column("metadata.createdAt", "CREATED")
```

## Caching

### Using the Cache

```python
from dtiam.utils.cache import cache, cached

# Direct cache usage
cache.set("key", {"data": "value"}, ttl=300)
value = cache.get("key")  # Returns None if expired
cache.delete("key")

# Cache statistics
stats = cache.stats()
# {
#     "total_entries": 10,
#     "active_entries": 8,
#     "expired_entries": 2,
#     "hits": 50,
#     "misses": 10,
#     "hit_rate": 83.33,
#     "default_ttl": 300
# }

# Clear cache
count = cache.clear()  # Clear all
count = cache.clear_expired()  # Clear only expired
count = cache.clear_prefix("groups:")  # Clear by prefix

# Reset statistics
cache.reset_stats()

# Get all keys
keys = cache.keys()
```

### Cache Decorator

```python
from dtiam.utils.cache import cached

@cached(ttl=300, prefix="groups")
def get_all_groups():
    return client.get("/groups").json()

# First call - hits API
groups = get_all_groups()

# Subsequent calls within TTL - returns cached data
groups = get_all_groups()
```

## Permissions Analysis

### Effective Permissions

```python
from dtiam.utils.permissions import PermissionsCalculator

calculator = PermissionsCalculator(client)

# User effective permissions
user_perms = calculator.get_user_effective_permissions("user@example.com")
# {
#     "user": {"uid": "...", "email": "..."},
#     "groups": [...],
#     "effective_permissions": [
#         {"effect": "ALLOW", "action": "settings:objects:read", "sources": [...]}
#     ],
#     "permission_count": 10
# }

# Group effective permissions
group_perms = calculator.get_group_effective_permissions("LOB5")
```

### Effective Permissions API (Direct)

```python
from dtiam.utils.permissions import EffectivePermissionsAPI

api = EffectivePermissionsAPI(client)

# Get effective permissions for a user (by email or UID)
result = api.get_user_effective_permissions(
    user_id="user@example.com",
    level_type="account",  # "account" or "environment"
    level_id=None,  # defaults to client.account_uuid
    services=["settings", "automation"],  # optional filter
)
# {
#     "effectivePermissions": [
#         {"permission": "settings:objects:read", "effect": "ALLOW", ...},
#         {"permission": "automation:workflows:read", "effect": "ALLOW", ...}
#     ],
#     "total": 25,
#     "pageSize": 100,
#     "pageNumber": 1
# }

# Get effective permissions for a group (by name or UUID)
result = api.get_group_effective_permissions(
    group_id="LOB5",
    level_type="account",
)

# Low-level API with pagination control
result = api.get_effective_permissions(
    entity_id="user-uid-here",
    entity_type="user",  # "user" or "group"
    level_type="account",
    level_id="abc-123-def",
    page=1,
    page_size=100,
)
```

### Permissions Matrix

```python
from dtiam.utils.permissions import PermissionsMatrix

matrix = PermissionsMatrix(client)

# Policy matrix
policy_matrix = matrix.generate_policy_matrix()
# {
#     "permissions": ["settings:objects:read", ...],
#     "matrix": [
#         {"policy_name": "admin", "settings:objects:read": True, ...}
#     ]
# }

# Group matrix
group_matrix = matrix.generate_group_matrix()
```

### Statement Parsing

```python
from dtiam.utils.permissions import parse_statement_query

statement = "ALLOW settings:objects:read; DENY settings:objects:write WHERE environment.tag.equals('prod');"
permissions = parse_statement_query(statement)
# [
#     {"effect": "ALLOW", "action": "settings:objects:read", "conditions": None},
#     {"effect": "DENY", "action": "settings:objects:write", "conditions": "environment.tag.equals('prod')"}
# ]
```

## Templates

### Template Manager

```python
from dtiam.utils.templates import TemplateManager, TemplateRenderer

manager = TemplateManager()

# List available templates
templates = manager.list_templates()
# [{"name": "group-team", "kind": "Group", "source": "builtin", ...}]

# Get template definition
template = manager.get_template("group-team")

# Get required variables
variables = manager.get_template_variables("group-team")
# [{"name": "team_name", "required": True}, ...]

# Render a template
rendered = manager.render_template("group-team", {
    "team_name": "LOB5",
    "description": "LOB5 team"
})
# {"kind": "Group", "spec": {"name": "LOB5", ...}}
```

### Custom Templates

```python
# Save a custom template
manager.save_template(
    name="my-template",
    kind="Group",
    template={
        "name": "{{ group_name }}",
        "description": "{{ description | default('') }}"
    },
    description="My custom template"
)

# Delete a template
manager.delete_template("my-template")

# Get templates directory
print(manager.templates_dir)
```

### Template Rendering

```python
from dtiam.utils.templates import TemplateRenderer

renderer = TemplateRenderer()

# Render template with variables
template = {
    "name": "{{ team_name }}",
    "description": "{{ description | default('No description') }}",
    "members": ["{{ lead_email }}"]
}

result = renderer.render(template, {
    "team_name": "LOB5",
    "lead_email": "lead@example.com"
})
# {"name": "LOB5", "description": "No description", "members": ["lead@example.com"]}
```

## Authentication

dtiam supports two authentication methods:

### Option 1: OAuth2 Token Manager (Recommended)

The `TokenManager` class handles OAuth2 client credentials flow with automatic token refresh. This is recommended for automation and long-running processes.

```python
from dtiam.utils.auth import TokenManager

# Create manager with OAuth2 credentials
token_manager = TokenManager(
    client_id="dt0s01.XXXX",
    client_secret="dt0s01.XXXX.YYYY",
    account_uuid="abc-123-def"
)

# Get authentication headers (auto-refreshes if expired)
headers = token_manager.get_headers()
# {"Authorization": "Bearer eyJ..."}

# Check if token is valid
is_valid = token_manager.is_token_valid()

# Force token refresh
token_manager._refresh_token()

# Clean up
token_manager.close()
```

### Option 2: Static Bearer Token

The `StaticTokenManager` class uses a pre-existing bearer token. **Warning:** Static tokens do NOT auto-refresh and will fail when expired.

```python
from dtiam.utils.auth import StaticTokenManager

# Create manager with static bearer token
# WARNING: Token will NOT auto-refresh!
token_manager = StaticTokenManager(token="dt0c01.XXXX.YYYY...")

# Get authentication headers
headers = token_manager.get_headers()
# {"Authorization": "Bearer dt0c01.XXXX.YYYY..."}

# Check if token exists (cannot verify expiration)
is_valid = token_manager.is_token_valid()
```

**When to use Static Bearer Token:**
- Quick testing and debugging
- Interactive sessions with short-lived tokens
- Integration with external token providers
- One-off operations

**When NOT to use Static Bearer Token:**
- Automation scripts (use OAuth2)
- CI/CD pipelines (use OAuth2)
- Long-running processes (use OAuth2)
- Production environments (use OAuth2)

### Using with Client

```python
from dtiam.client import Client
from dtiam.utils.auth import TokenManager, StaticTokenManager

# OAuth2 (recommended)
oauth_manager = TokenManager(
    client_id="dt0s01.XXXX",
    client_secret="dt0s01.XXXX.YYYY",
    account_uuid="abc-123-def"
)
client = Client(account_uuid="abc-123-def", token_manager=oauth_manager)

# Static bearer token (for testing only)
static_manager = StaticTokenManager(token="dt0c01.XXXX...")
client = Client(account_uuid="abc-123-def", token_manager=static_manager)
```

### Environment Variable Authentication

```python
import os

# OAuth2 via environment variables
os.environ["DTIAM_CLIENT_ID"] = "dt0s01.XXXX"
os.environ["DTIAM_CLIENT_SECRET"] = "dt0s01.XXXX.YYYY"
os.environ["DTIAM_ACCOUNT_UUID"] = "abc-123-def"

# OR bearer token via environment variables
os.environ["DTIAM_BEARER_TOKEN"] = "dt0c01.XXXX..."
os.environ["DTIAM_ACCOUNT_UUID"] = "abc-123-def"

# Create client from environment
from dtiam.client import create_client_from_config
client = create_client_from_config()  # Auto-detects auth method
```

## Complete Example

```python
from dtiam.config import load_config
from dtiam.client import create_client_from_config
from dtiam.resources.groups import GroupHandler
from dtiam.resources.policies import PolicyHandler
from dtiam.resources.bindings import BindingHandler
from dtiam.output import Printer, OutputFormat

def main():
    # Load configuration
    config = load_config()

    # Create client
    with create_client_from_config(config, verbose=True) as client:
        # Initialize handlers
        group_handler = GroupHandler(client)
        policy_handler = PolicyHandler(
            client,
            level_type="account",
            level_id=client.account_uuid
        )
        binding_handler = BindingHandler(client)

        # Create a group
        group = group_handler.create(
            name="LOB5",
            description="LOB5 team with standard access",
        )
        print(f"Created group: {group['name']}")

        # Find a policy
        policy = policy_handler.get_by_name("developer-policy")
        if not policy:
            print("Policy not found!")
            return

        # Create binding
        binding_handler.create(
            group_uuid=group["uuid"],
            policy_uuid=policy["uuid"]
        )
        print(f"Bound policy: {policy['name']}")

        # List all groups with output formatting
        printer = Printer(format=OutputFormat.TABLE)
        groups = group_handler.list()
        printer.print(groups)

if __name__ == "__main__":
    main()
```

## See Also

- [Architecture](ARCHITECTURE.md)
- [Command Reference](COMMANDS.md)
- [Quick Start Guide](QUICK_START.md)
