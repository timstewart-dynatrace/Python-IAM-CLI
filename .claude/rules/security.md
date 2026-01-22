# Security Requirements

This document defines security requirements and best practices for the dtiam project.

## Credential Handling

### Never Log Secrets

- Never log full credentials, tokens, or secrets
- Use masking for any credential display

```python
from dtiam.config import mask_secret

# WRONG - exposes secret
logger.info(f"Using client secret: {client_secret}")

# CORRECT - masks sensitive data
logger.info(f"Using client secret: {mask_secret(client_secret)}")
```

### Secure Storage

- Credentials stored in `~/.config/dtiam/config` (XDG compliant)
- File permissions should be restrictive (0600)
- Never commit credentials to version control

### Token Expiration

- OAuth2 tokens auto-refresh (recommended)
- Static bearer tokens expire and cannot be refreshed
- Log warnings when using static tokens

```python
if using_static_token:
    logger.warning(
        "Using static bearer token. Token will NOT auto-refresh. "
        "Requests will fail when token expires."
    )
```

## Input Validation

### Validate User Input

- Validate all user-provided identifiers
- Sanitize inputs before API calls
- Use Pydantic models for structured data

```python
from pydantic import BaseModel, Field, validator

class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)

    @validator("name")
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Group name cannot be empty or whitespace")
        return v.strip()
```

### UUID Validation

- Validate UUIDs before API calls
- Use proper UUID format checking

```python
import re

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

def is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    return bool(UUID_PATTERN.match(value))
```

## API Security

### OAuth2 Scopes

Request only necessary scopes:

```python
# Default scopes - request only what's needed
IAM_SCOPES = (
    "account-idm-read iam:users:read iam:groups:read account-idm-write "
    "account-env-read account-env-write account-uac-read account-uac-write "
    "iam-policies-management iam:policies:write "
    "iam:policies:read iam:bindings:write iam:bindings:read "
    "iam:effective-permissions:read "
    "iam:boundaries:read iam:boundaries:write"
)
```

### Scope Validation

Check granted scopes and warn about missing ones:

```python
def _refresh_token(self) -> None:
    # ... token refresh logic ...

    # Check if granted scopes differ from requested
    requested_scopes = set(self.scope.split())
    granted_scopes = set(granted_scope.split())
    missing_scopes = requested_scopes - granted_scopes

    if missing_scopes:
        logger.warning(
            f"Some requested scopes were not granted: {' '.join(sorted(missing_scopes))}"
        )
        logger.warning(
            "API calls requiring these scopes will fail. "
            "Check your OAuth client configuration in Dynatrace."
        )
```

### HTTPS Only

- All API calls must use HTTPS
- Never allow HTTP for production
- Validate SSL certificates

```python
DEFAULT_IAM_API_BASE = "https://api.dynatrace.com/iam/v1"  # HTTPS only
```

## Error Handling

### Don't Expose Internal Details

- Sanitize error messages shown to users
- Log detailed errors internally, show summary externally

```python
try:
    response = self.client.post(path, json=data)
except APIError as e:
    # Log full details internally
    logger.error(f"API error: {e.status_code} - {e.response_body}")

    # Show sanitized message to user
    if e.status_code == 401:
        console.print("[red]Error:[/red] Authentication failed. Check your credentials.")
    elif e.status_code == 403:
        console.print("[red]Error:[/red] Permission denied for this operation.")
    else:
        console.print(f"[red]Error:[/red] Request failed: {e.status_code}")
```

### Prevent Information Leakage

- Don't include stack traces in user output
- Don't expose internal paths or configurations

## Sensitive Operations

### Destructive Operations

Require confirmation for destructive operations:

```python
@app.command("delete")
def delete_group(
    group_id: str = typer.Argument(...),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a group."""
    if not force:
        confirm = typer.confirm(f"Delete group '{group_id}'? This cannot be undone.")
        if not confirm:
            console.print("Aborted.")
            raise typer.Exit(0)

    # Proceed with deletion
```

### Dry Run Mode

Support dry-run for bulk operations:

```python
@app.command("bulk-create")
def bulk_create(
    file: Path = typer.Argument(...),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run"),
) -> None:
    """Bulk create resources."""
    if dry_run:
        console.print("[yellow]DRY RUN MODE - No changes will be made[/yellow]")
        # Show what would happen
    else:
        # Actually perform changes
```

## Audit Logging

### Log Security-Relevant Events

```python
# Log authentication events
logger.info("OAuth2 token retrieved successfully")
logger.warning("Token refresh failed, attempting re-authentication")

# Log destructive operations
logger.info(f"Deleting group: {group_id}")
logger.info(f"Creating policy binding: group={group_id}, policy={policy_id}")

# Log permission issues
logger.warning(f"Permission denied for operation: {operation}")
```

## Environment Security

### Environment Variables

- Support environment variable overrides for CI/CD
- Never require secrets in command-line arguments
- Document security implications

```python
# Supported environment variables
DTIAM_CLIENT_SECRET  # OAuth2 secret (never log)
DTIAM_BEARER_TOKEN   # Static token (never log)
DTIAM_ACCOUNT_UUID   # Account ID (safe to log)
```

### Files with Secrets

- `.env` files should be in `.gitignore`
- Config files should have restricted permissions
- Document secure configuration practices

## Checklist for New Features

When adding new features, verify:

- [ ] No secrets are logged or displayed in full
- [ ] Input is validated before API calls
- [ ] Destructive operations require confirmation
- [ ] Error messages don't expose internal details
- [ ] HTTPS is used for all external communication
- [ ] OAuth scopes are appropriate and documented
- [ ] Audit logging covers security-relevant events
