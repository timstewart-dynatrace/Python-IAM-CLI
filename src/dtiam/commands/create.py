"""Create command for creating IAM resources."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from dtiam.client import create_client_from_config
from dtiam.config import load_config
from dtiam.output import OutputFormat, Printer

app = typer.Typer(no_args_is_help=True)
console = Console()


def get_context() -> str | None:
    """Get context override from CLI state."""
    from dtiam.cli import state
    return state.context


def is_verbose() -> bool:
    """Check if verbose mode is enabled."""
    from dtiam.cli import state
    return state.verbose


def is_dry_run() -> bool:
    """Check if dry-run mode is enabled."""
    from dtiam.cli import state
    return state.dry_run


def get_output_format() -> OutputFormat:
    """Get output format from CLI state."""
    from dtiam.cli import state
    return state.output


def is_plain_mode() -> bool:
    """Check if plain mode is enabled."""
    from dtiam.cli import state
    return state.plain


def get_api_url() -> str | None:
    """Get API URL override from CLI state."""
    from dtiam.cli import state
    return state.api_url


@app.command("group")
def create_group(
    name: str = typer.Option(..., "--name", "-n", help="Group name"),
    description: str = typer.Option("", "--description", "-d", help="Group description"),
    output: OutputFormat | None = typer.Option(None, "-o", "--output"),
) -> None:
    """Create a new IAM group."""
    from dtiam.resources.groups import GroupHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = GroupHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    data = {
        "name": name,
        "description": description,
    }

    if is_dry_run():
        console.print("[yellow]Dry-run mode:[/yellow] Would create group:")
        printer.print(data)
        return

    try:
        result = handler.create(data)
        console.print(f"[green]Created group:[/green] {result.get('name', name)}")
        printer.print(result)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to create group: {e}")
        raise typer.Exit(1)
    finally:
        client.close()


@app.command("policy")
def create_policy(
    name: str = typer.Option(..., "--name", "-n", help="Policy name"),
    statement: str = typer.Option(..., "--statement", "-s", help="Policy statement query"),
    description: str = typer.Option("", "--description", "-d", help="Policy description"),
    level: str = typer.Option("account", "--level", "-l", help="Policy level (account)"),
    output: OutputFormat | None = typer.Option(None, "-o", "--output"),
) -> None:
    """Create a new IAM policy."""
    from dtiam.resources.policies import PolicyHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())

    level_type = "account"  # Only account-level policies can be created
    level_id = client.account_uuid

    handler = PolicyHandler(client, level_type=level_type, level_id=level_id)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    data = {
        "name": name,
        "statementQuery": statement,
        "description": description,
    }

    if is_dry_run():
        console.print("[yellow]Dry-run mode:[/yellow] Would create policy:")
        printer.print(data)
        return

    try:
        result = handler.create(data)
        console.print(f"[green]Created policy:[/green] {result.get('name', name)}")
        printer.print(result)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to create policy: {e}")
        raise typer.Exit(1)
    finally:
        client.close()


@app.command("binding")
def create_binding(
    group: str = typer.Option(..., "--group", "-g", help="Group UUID"),
    policy: str = typer.Option(..., "--policy", "-p", help="Policy UUID"),
    boundary: str | None = typer.Option(None, "--boundary", "-b", help="Boundary UUID"),
    output: OutputFormat | None = typer.Option(None, "-o", "--output"),
) -> None:
    """Create a policy binding (bind a policy to a group)."""
    from dtiam.resources.bindings import BindingHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = BindingHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    boundaries = [boundary] if boundary else []

    if is_dry_run():
        console.print("[yellow]Dry-run mode:[/yellow] Would create binding:")
        console.print(f"  Group: {group}")
        console.print(f"  Policy: {policy}")
        if boundaries:
            console.print(f"  Boundaries: {', '.join(boundaries)}")
        return

    try:
        result = handler.create(group_uuid=group, policy_uuid=policy, boundaries=boundaries)
        console.print("[green]Created binding[/green]")
        printer.print(result)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to create binding: {e}")
        raise typer.Exit(1)
    finally:
        client.close()


@app.command("boundary")
def create_boundary(
    name: str = typer.Option(..., "--name", "-n", help="Boundary name"),
    zones: str | None = typer.Option(None, "--zones", "-z", help="Management zones (comma-separated)"),
    query: str | None = typer.Option(None, "--query", "-q", help="Custom boundary query"),
    description: str = typer.Option("", "--description", "-d", help="Boundary description"),
    output: OutputFormat | None = typer.Option(None, "-o", "--output"),
) -> None:
    """Create a new IAM policy boundary.

    Either --zones or --query must be provided.
    --zones auto-generates a boundary query for the specified management zones.
    --query allows specifying a custom boundary query.
    """
    from dtiam.resources.boundaries import BoundaryHandler

    if not zones and not query:
        console.print("[red]Error:[/red] Either --zones or --query must be provided.")
        raise typer.Exit(1)

    if zones and query:
        console.print("[red]Error:[/red] Cannot use both --zones and --query. Choose one.")
        raise typer.Exit(1)

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = BoundaryHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        if zones:
            zone_list = [z.strip() for z in zones.split(",") if z.strip()]
            result = handler.create_from_zones(name=name, management_zones=zone_list, description=description)
        else:
            result = handler.create(name=name, boundary_query=query, description=description)

        if is_dry_run():
            console.print("[yellow]Dry-run mode:[/yellow] Would create boundary:")
            printer.print(result if isinstance(result, dict) else {"name": name, "zones": zones or query})
            return

        console.print(f"[green]Created boundary:[/green] {result.get('name', name)}")
        printer.print(result)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to create boundary: {e}")
        raise typer.Exit(1)
    finally:
        client.close()


@app.command("service-user")
def create_service_user(
    name: str = typer.Option(..., "--name", "-n", help="Service user name"),
    description: str = typer.Option("", "--description", "-d", help="Description"),
    groups: str = typer.Option("", "--groups", "-g", help="Comma-separated group UUIDs or names"),
    output: OutputFormat | None = typer.Option(None, "-o", "--output"),
    save_credentials: Path | None = typer.Option(
        None, "--save-credentials", "-s",
        help="Save client credentials to file"
    ),
) -> None:
    """Create a new service user (OAuth client).

    Creates a service user and returns client credentials.
    IMPORTANT: Save the client secret - it cannot be retrieved later!

    Example:
        dtiam create service-user --name "CI Pipeline"
        dtiam create service-user --name "CI Pipeline" --groups "DevOps,Automation"
        dtiam create service-user --name "CI Pipeline" --save-credentials creds.json
    """
    import json

    from dtiam.resources.groups import GroupHandler
    from dtiam.resources.service_users import ServiceUserHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = ServiceUserHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        # Resolve groups if provided
        group_uuids: list[str] = []
        if groups:
            group_handler = GroupHandler(client)
            for group_ref in groups.split(","):
                group_ref = group_ref.strip()
                if not group_ref:
                    continue

                group_obj = group_handler.get(group_ref)
                if not group_obj:
                    group_obj = group_handler.get_by_name(group_ref)

                if group_obj:
                    group_uuids.append(group_obj.get("uuid", ""))
                else:
                    console.print(f"[yellow]Warning:[/yellow] Group '{group_ref}' not found, skipping.")

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would create service user '{name}'")
            if description:
                console.print(f"  Description: {description}")
            if group_uuids:
                console.print(f"  Groups: {len(group_uuids)} groups")
            return

        result = handler.create(
            name=name,
            description=description if description else None,
            groups=group_uuids if group_uuids else None,
        )

        if result:
            console.print(f"[green]Created service user:[/green] {name}")

            # Warn about credentials
            client_id = result.get("clientId", result.get("client_id", ""))
            client_secret = result.get("clientSecret", result.get("client_secret", ""))

            if client_secret:
                console.print("")
                console.print("[yellow]IMPORTANT: Save these credentials now![/yellow]")
                console.print("[yellow]The client secret cannot be retrieved later.[/yellow]")
                console.print("")
                console.print(f"Client ID:     {client_id}")
                console.print(f"Client Secret: {client_secret}")

                if save_credentials:
                    creds = {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "name": name,
                    }
                    save_credentials.write_text(json.dumps(creds, indent=2))
                    console.print(f"\n[green]Credentials saved to:[/green] {save_credentials}")

            printer.print(result)
        else:
            console.print(f"[red]Error:[/red] Failed to create service user '{name}'")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("platform-token")
def create_platform_token(
    name: str = typer.Option(..., "--name", "-n", help="Token name/description"),
    scopes: str | None = typer.Option(
        None, "--scopes", "-s",
        help="Comma-separated list of scopes for the token"
    ),
    expires_in: str | None = typer.Option(
        None, "--expires-in", "-e",
        help="Token expiration (e.g., '30d', '1y', '365d')"
    ),
    output: OutputFormat | None = typer.Option(None, "-o", "--output"),
    save_token: Path | None = typer.Option(
        None, "--save-token",
        help="Save token value to file"
    ),
) -> None:
    """Generate a new platform token.

    Creates a platform token and returns the token value.
    IMPORTANT: Save the token value - it cannot be retrieved later!

    Requires the `platform-token:tokens:manage` scope.

    Example:
        dtiam create platform-token --name "CI Pipeline Token"
        dtiam create platform-token --name "Automation" --expires-in 30d
        dtiam create platform-token --name "CI Token" --save-token token.txt
        dtiam create platform-token --name "Custom" --scopes "account-idm-read,account-env-read"
    """
    from dtiam.resources.platform_tokens import PlatformTokenHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = PlatformTokenHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        # Parse scopes if provided
        scope_list: list[str] | None = None
        if scopes:
            scope_list = [s.strip() for s in scopes.split(",") if s.strip()]

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would create platform token '{name}'")
            if scope_list:
                console.print(f"  Scopes: {', '.join(scope_list)}")
            if expires_in:
                console.print(f"  Expires in: {expires_in}")
            return

        result = handler.create(
            name=name,
            scopes=scope_list,
            expires_in=expires_in,
        )

        if result:
            console.print(f"[green]Created platform token:[/green] {name}")

            # Get the token value - check various possible field names
            token_value = result.get("token", result.get("value", result.get("tokenValue", "")))

            if token_value:
                console.print("")
                console.print("[yellow]IMPORTANT: Save this token now![/yellow]")
                console.print("[yellow]The token value cannot be retrieved later.[/yellow]")
                console.print("")
                console.print(f"Token: {token_value}")

                if save_token:
                    save_token.write_text(token_value)
                    console.print(f"\n[green]Token saved to:[/green] {save_token}")

            # Print full result for structured output
            if fmt in (OutputFormat.JSON, OutputFormat.YAML):
                printer.print(result)
        else:
            console.print(f"[red]Error:[/red] Failed to create platform token '{name}'")
            raise typer.Exit(1)

    finally:
        client.close()
