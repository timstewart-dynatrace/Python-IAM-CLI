"""Configuration management commands.

Provides commands for managing contexts, OAuth2 credentials, and preferences.
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from dtiam.config import (
    load_config,
    save_config,
    get_config_path,
    mask_secret,
)
from dtiam.utils.auth import extract_client_id_from_secret

app = typer.Typer(no_args_is_help=True, help="Manage dtiam configuration")
console = Console()


@app.command("view")
def view_config(
    show_secrets: bool = typer.Option(
        False,
        "--show-secrets",
        help="Show full credential values (security risk)",
    ),
) -> None:
    """Display the current configuration."""
    import yaml

    config = load_config()

    # Mask credentials for security
    data = config.model_dump(by_alias=True)
    if not show_secrets:
        for cred in data.get("credentials", []):
            if cred.get("credential"):
                cred_data = cred["credential"]
                if cred_data.get("client-id"):
                    cred_data["client-id"] = mask_secret(cred_data["client-id"])
                if cred_data.get("client-secret"):
                    cred_data["client-secret"] = mask_secret(cred_data["client-secret"])

    console.print(yaml.dump(data, default_flow_style=False, sort_keys=False))


@app.command("get-contexts")
def get_contexts() -> None:
    """List all configured contexts."""
    config = load_config()

    if not config.contexts:
        console.print("No contexts configured.")
        console.print("Use 'dtiam config set-context <name>' to create one.")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("CURRENT")
    table.add_column("NAME")
    table.add_column("ACCOUNT-UUID")
    table.add_column("CREDENTIALS-REF")

    for ctx in config.contexts:
        current = "*" if ctx.name == config.current_context else ""
        table.add_row(
            current,
            ctx.name,
            ctx.context.account_uuid,
            ctx.context.credentials_ref,
        )

    console.print(table)


@app.command("current-context")
def current_context() -> None:
    """Display the current context name."""
    config = load_config()

    if not config.current_context:
        console.print("No current context set.")
        console.print("Use 'dtiam config use-context <name>' to set one.")
        raise typer.Exit(1)

    console.print(config.current_context)


@app.command("use-context")
def use_context(
    name: str = typer.Argument(..., help="Context name to switch to"),
) -> None:
    """Switch to a different context."""
    config = load_config()

    if not config.get_context(name):
        console.print(f"[red]Error:[/red] Context '{name}' not found.")
        available = [ctx.name for ctx in config.contexts]
        if available:
            console.print(f"Available contexts: {', '.join(available)}")
        raise typer.Exit(1)

    config.current_context = name
    save_config(config)
    console.print(f"Switched to context '{name}'.")


@app.command("set-context")
def set_context(
    name: str = typer.Argument(..., help="Context name"),
    account_uuid: Optional[str] = typer.Option(
        None,
        "--account-uuid",
        "-a",
        help="Dynatrace account UUID",
    ),
    credentials_ref: Optional[str] = typer.Option(
        None,
        "--credentials-ref",
        "-c",
        help="Reference to a named credential",
    ),
    set_current: bool = typer.Option(
        False,
        "--current",
        help="Set as current context",
    ),
) -> None:
    """Create or update a context.

    Examples:
        dtiam config set-context prod --account-uuid abc-123 --credentials-ref prod-creds
        dtiam config set-context dev -a xyz-789 -c dev-creds --current
    """
    config = load_config()

    existing = config.get_context(name)

    if not existing and (not account_uuid or not credentials_ref):
        console.print("[red]Error:[/red] New context requires --account-uuid and --credentials-ref")
        raise typer.Exit(1)

    try:
        config.set_context(name, account_uuid, credentials_ref)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if set_current:
        config.current_context = name

    save_config(config)

    action = "Updated" if existing else "Created"
    console.print(f"{action} context '{name}'.")
    if set_current:
        console.print(f"Switched to context '{name}'.")


@app.command("delete-context")
def delete_context(
    name: str = typer.Argument(..., help="Context name to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a context."""
    config = load_config()

    if not config.get_context(name):
        console.print(f"[red]Error:[/red] Context '{name}' not found.")
        raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(f"Delete context '{name}'?")
        if not confirm:
            console.print("Aborted.")
            raise typer.Exit(0)

    config.delete_context(name)
    save_config(config)
    console.print(f"Deleted context '{name}'.")


@app.command("set-credentials")
def set_credentials(
    name: str = typer.Argument(..., help="Credential name"),
    client_id: Optional[str] = typer.Option(
        None,
        "--client-id",
        "-i",
        help="OAuth2 client ID (auto-extracted from secret if not provided)",
    ),
    client_secret: Optional[str] = typer.Option(
        None,
        "--client-secret",
        "-s",
        help="OAuth2 client secret (will prompt if not provided)",
    ),
    account_uuid: Optional[str] = typer.Option(
        None,
        "--account-uuid",
        "-a",
        help="Dynatrace account UUID (will prompt if not provided)",
    ),
    environment_url: Optional[str] = typer.Option(
        None,
        "--environment-url",
        "-e",
        help="Dynatrace environment URL (will prompt if not provided)",
    ),
    environment_token: Optional[str] = typer.Option(
        None,
        "--environment-token",
        "-t",
        help="Optional environment API token",
    ),
    api_url: Optional[str] = typer.Option(
        None,
        "--api-url",
        help="Custom IAM API base URL (e.g., for testing)",
    ),
    scopes: Optional[str] = typer.Option(
        None,
        "--scopes",
        help="OAuth2 scopes (space-separated). Uses defaults if not set.",
    ),
) -> None:
    """Store OAuth2 credentials and environment settings.

    The client ID is automatically extracted from the client secret since
    Dynatrace secrets follow the format: dt0s01.CLIENTID.SECRETPART
    where the client ID is dt0s01.CLIENTID.

    Examples:
        # Store credentials (client ID auto-extracted from secret)
        dtiam config set-credentials prod-creds \\
          --client-secret dt0s01.XXX.YYY \\
          --account-uuid abc-123 \\
          --environment-url https://abc123.live.dynatrace.com

        # Explicitly specify client ID (overrides auto-extraction)
        dtiam config set-credentials prod-creds \\
          --client-id dt0s01.XXX \\
          --client-secret dt0s01.XXX.YYY \\
          --account-uuid abc-123

        # Update just the environment token (existing credential)
        dtiam config set-credentials prod-creds --environment-token dt0c01.XXX

        # Store credentials with custom API URL (for testing)
        dtiam config set-credentials test-creds \\
          --client-secret dt0s01.XXX.YYY \\
          --account-uuid abc-123 \\
          --api-url https://custom-api.example.com/iam/v1

        # Interactive prompt for required values (new credential)
        dtiam config set-credentials dev-creds
    """
    config = load_config()

    # Check if credential already exists
    existing_cred = config.get_credential(name)

    if existing_cred:
        # Update existing credential - only update provided fields
        updated = False

        if client_secret:
            existing_cred.client_secret = client_secret
            updated = True
            # Auto-extract and update client ID when secret changes (unless explicitly provided)
            if not client_id:
                extracted_id = extract_client_id_from_secret(client_secret)
                if extracted_id:
                    existing_cred.client_id = extracted_id
                    console.print(f"Auto-extracted client ID: {mask_secret(extracted_id)}")
        if client_id:
            existing_cred.client_id = client_id
            updated = True
        if environment_url:
            existing_cred.environment_url = environment_url
            updated = True
        if environment_token:
            existing_cred.environment_token = environment_token
            updated = True
        if api_url:
            existing_cred.api_url = api_url
            updated = True
        if scopes:
            existing_cred.scopes = scopes
            updated = True

        if not updated:
            console.print(f"[yellow]Warning:[/yellow] No changes specified for '{name}'.")
            console.print("Use --client-id, --client-secret, --environment-url, --environment-token, --api-url, or --scopes to update.")
            raise typer.Exit(1)

        # Update context environment-url if provided
        if environment_url:
            existing_ctx = config.get_context(name)
            if existing_ctx:
                existing_ctx.environment_url = environment_url

        save_config(config)
        console.print(f"Updated credentials '{name}'.")
        return

    # New credential - require client-secret, account-uuid (client-id auto-extracted)
    if not client_secret:
        client_secret = typer.prompt("Enter OAuth2 client secret", hide_input=True)

    if not client_secret:
        console.print("[red]Error:[/red] Client secret cannot be empty.")
        raise typer.Exit(1)

    # Auto-extract client ID from secret if not provided
    if not client_id:
        client_id = extract_client_id_from_secret(client_secret)
        if client_id:
            console.print(f"Auto-extracted client ID: {mask_secret(client_id)}")
        else:
            # Fall back to prompting if extraction failed
            client_id = typer.prompt("Enter OAuth2 client ID (could not auto-extract)")

    if not client_id:
        console.print("[red]Error:[/red] Client ID cannot be empty.")
        raise typer.Exit(1)

    if not account_uuid:
        account_uuid = typer.prompt("Enter account UUID")

    if not account_uuid:
        console.print("[red]Error:[/red] Account UUID cannot be empty.")
        raise typer.Exit(1)

    if not environment_url:
        environment_url = typer.prompt(
            "Enter environment URL (e.g., https://abc123.live.dynatrace.com)",
            default="",
        ) or None

    config.set_credential(name, client_id, client_secret, environment_url, environment_token, api_url, scopes)
    config.set_context(name, account_uuid, name, environment_url)
    save_config(config)
    console.print(f"Stored credentials as '{name}'.")
    console.print(f"Created context '{name}' with account UUID {account_uuid}.")
    if environment_url:
        console.print(f"Environment URL: {environment_url}")
    if api_url:
        console.print(f"API URL: {api_url}")
    if scopes:
        console.print(f"Scopes: {scopes}")


@app.command("delete-credentials")
def delete_credentials(
    name: str = typer.Argument(..., help="Credential name to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete stored credentials."""
    config = load_config()

    if not config.get_credential(name):
        console.print(f"[red]Error:[/red] Credential '{name}' not found.")
        raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(f"Delete credential '{name}'?")
        if not confirm:
            console.print("Aborted.")
            raise typer.Exit(0)

    config.delete_credential(name)
    save_config(config)
    console.print(f"Deleted credential '{name}'.")


@app.command("get-credentials")
def get_credentials() -> None:
    """List all stored credentials."""
    config = load_config()

    if not config.credentials:
        console.print("No credentials configured.")
        console.print("Use 'dtiam config set-credentials <name>' to add credentials.")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("NAME")
    table.add_column("CLIENT-ID")

    for cred in config.credentials:
        table.add_row(
            cred.name,
            mask_secret(cred.credential.client_id),
        )

    console.print(table)


@app.command("path")
def config_path() -> None:
    """Display the configuration file path."""
    console.print(str(get_config_path()))
