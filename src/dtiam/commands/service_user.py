"""Service user management commands for IAM operations."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

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


@app.command("list")
def list_service_users(
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List all service users in the account.

    Example:
        dtiam service-user list
        dtiam service-user list -o json
    """
    from dtiam.resources.service_users import ServiceUserHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = ServiceUserHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        users = handler.list()

        if not users:
            console.print("No service users found.")
            return

        printer.print(
            users,
            [
                ("uid", "UID"),
                ("name", "NAME"),
                ("description", "DESCRIPTION"),
            ],
        )

    finally:
        client.close()


@app.command("get")
def get_service_user(
    user: str = typer.Argument(..., help="Service user UUID or name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Get details of a service user.

    Example:
        dtiam service-user get my-service-user
        dtiam service-user get abc-123-def -o json
    """
    from dtiam.resources.service_users import ServiceUserHandler
    from dtiam.commands.describe import print_detail_view

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = ServiceUserHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        # Try by UUID first, then by name
        user_obj = handler.get(user)
        if not user_obj:
            user_obj = handler.get_by_name(user)

        if not user_obj:
            console.print(f"[red]Error:[/red] Service user '{user}' not found.")
            raise typer.Exit(1)

        # Get expanded details
        user_id = user_obj.get("uid", "")
        result = handler.get_expanded(user_id)

        if output:
            printer.print(result)
        else:
            print_detail_view(result, f"Service User: {result.get('name', user)}")

    finally:
        client.close()


@app.command("create")
def create_service_user(
    name: str = typer.Option(..., "--name", "-n", help="Service user name"),
    description: str = typer.Option("", "--description", "-d", help="Description"),
    groups: str = typer.Option("", "--groups", "-g", help="Comma-separated group UUIDs or names"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
    save_credentials: Optional[Path] = typer.Option(
        None, "--save-credentials", "-s",
        help="Save client credentials to file"
    ),
) -> None:
    """Create a new service user (OAuth client).

    Creates a service user and returns client credentials.
    IMPORTANT: Save the client secret - it cannot be retrieved later!

    Example:
        dtiam service-user create --name "CI Pipeline"
        dtiam service-user create --name "CI Pipeline" --groups "DevOps,Automation"
        dtiam service-user create --name "CI Pipeline" --save-credentials creds.json
    """
    from dtiam.resources.service_users import ServiceUserHandler
    from dtiam.resources.groups import GroupHandler
    import json

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
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


@app.command("update")
def update_service_user(
    user: str = typer.Argument(..., help="Service user UUID or name"),
    name: str = typer.Option("", "--name", "-n", help="New name"),
    description: str = typer.Option("", "--description", "-d", help="New description"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Update a service user.

    Example:
        dtiam service-user update my-service-user --name "New Name"
        dtiam service-user update my-service-user --description "Updated description"
    """
    from dtiam.resources.service_users import ServiceUserHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = ServiceUserHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        # Resolve user
        user_obj = handler.get(user)
        if not user_obj:
            user_obj = handler.get_by_name(user)

        if not user_obj:
            console.print(f"[red]Error:[/red] Service user '{user}' not found.")
            raise typer.Exit(1)

        user_id = user_obj.get("uid", "")
        user_name = user_obj.get("name", user)

        if not name and not description:
            console.print("[yellow]No updates specified.[/yellow]")
            return

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would update service user '{user_name}'")
            if name:
                console.print(f"  New name: {name}")
            if description:
                console.print(f"  New description: {description}")
            return

        result = handler.update(
            user_id,
            name=name if name else None,
            description=description if description else None,
        )

        if result:
            console.print(f"[green]Updated service user:[/green] {user_name}")
            printer.print(result)
        else:
            console.print(f"[red]Error:[/red] Failed to update service user '{user_name}'")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("delete")
def delete_service_user(
    user: str = typer.Argument(..., help="Service user UUID or name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a service user.

    Example:
        dtiam service-user delete my-service-user
        dtiam service-user delete my-service-user --force
    """
    from dtiam.resources.service_users import ServiceUserHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = ServiceUserHandler(client)

    try:
        # Resolve user
        user_obj = handler.get(user)
        if not user_obj:
            user_obj = handler.get_by_name(user)

        if not user_obj:
            console.print(f"[red]Error:[/red] Service user '{user}' not found.")
            raise typer.Exit(1)

        user_id = user_obj.get("uid", "")
        user_name = user_obj.get("name", user)

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would delete service user '{user_name}'")
            return

        if not force:
            confirm = typer.confirm(
                f"Delete service user '{user_name}'? This will invalidate any OAuth tokens."
            )
            if not confirm:
                console.print("Aborted.")
                raise typer.Exit(0)

        success = handler.delete(user_id)

        if success:
            console.print(f"[green]Deleted service user:[/green] {user_name}")
        else:
            console.print(f"[red]Error:[/red] Failed to delete service user '{user_name}'")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("add-to-group")
def add_to_group(
    user: str = typer.Option(..., "--user", "-u", help="Service user UUID or name"),
    group: str = typer.Option(..., "--group", "-g", help="Group UUID or name"),
) -> None:
    """Add a service user to a group.

    Example:
        dtiam service-user add-to-group --user my-service-user --group DevOps
    """
    from dtiam.resources.service_users import ServiceUserHandler
    from dtiam.resources.groups import GroupHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = ServiceUserHandler(client)
    group_handler = GroupHandler(client)

    try:
        # Resolve service user
        user_obj = handler.get(user)
        if not user_obj:
            user_obj = handler.get_by_name(user)

        if not user_obj:
            console.print(f"[red]Error:[/red] Service user '{user}' not found.")
            raise typer.Exit(1)

        user_id = user_obj.get("uid", "")
        user_name = user_obj.get("name", user)

        # Resolve group
        group_obj = group_handler.get(group)
        if not group_obj:
            group_obj = group_handler.get_by_name(group)

        if not group_obj:
            console.print(f"[red]Error:[/red] Group '{group}' not found.")
            raise typer.Exit(1)

        group_uuid = group_obj.get("uuid", "")
        group_name = group_obj.get("name", group)

        if is_dry_run():
            console.print(
                f"[yellow]Dry-run mode:[/yellow] Would add service user '{user_name}' to group '{group_name}'"
            )
            return

        success = handler.add_to_group(user_id, group_uuid)

        if success:
            console.print(f"[green]Added service user[/green] '{user_name}' to group '{group_name}'")
        else:
            console.print(f"[red]Error:[/red] Failed to add service user to group")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("remove-from-group")
def remove_from_group(
    user: str = typer.Option(..., "--user", "-u", help="Service user UUID or name"),
    group: str = typer.Option(..., "--group", "-g", help="Group UUID or name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Remove a service user from a group.

    Example:
        dtiam service-user remove-from-group --user my-service-user --group DevOps
    """
    from dtiam.resources.service_users import ServiceUserHandler
    from dtiam.resources.groups import GroupHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = ServiceUserHandler(client)
    group_handler = GroupHandler(client)

    try:
        # Resolve service user
        user_obj = handler.get(user)
        if not user_obj:
            user_obj = handler.get_by_name(user)

        if not user_obj:
            console.print(f"[red]Error:[/red] Service user '{user}' not found.")
            raise typer.Exit(1)

        user_id = user_obj.get("uid", "")
        user_name = user_obj.get("name", user)

        # Resolve group
        group_obj = group_handler.get(group)
        if not group_obj:
            group_obj = group_handler.get_by_name(group)

        if not group_obj:
            console.print(f"[red]Error:[/red] Group '{group}' not found.")
            raise typer.Exit(1)

        group_uuid = group_obj.get("uuid", "")
        group_name = group_obj.get("name", group)

        if is_dry_run():
            console.print(
                f"[yellow]Dry-run mode:[/yellow] Would remove service user '{user_name}' from group '{group_name}'"
            )
            return

        if not force:
            confirm = typer.confirm(
                f"Remove service user '{user_name}' from group '{group_name}'?"
            )
            if not confirm:
                console.print("Aborted.")
                raise typer.Exit(0)

        success = handler.remove_from_group(user_id, group_uuid)

        if success:
            console.print(f"[green]Removed service user[/green] '{user_name}' from group '{group_name}'")
        else:
            console.print(f"[red]Error:[/red] Failed to remove service user from group")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("list-groups")
def list_groups(
    user: str = typer.Argument(..., help="Service user UUID or name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List all groups a service user belongs to.

    Example:
        dtiam service-user list-groups my-service-user
    """
    from dtiam.resources.service_users import ServiceUserHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = ServiceUserHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        # Resolve service user
        user_obj = handler.get(user)
        if not user_obj:
            user_obj = handler.get_by_name(user)

        if not user_obj:
            console.print(f"[red]Error:[/red] Service user '{user}' not found.")
            raise typer.Exit(1)

        user_id = user_obj.get("uid", "")
        user_name = user_obj.get("name", user)

        groups = handler.get_groups(user_id)

        if not groups:
            console.print(f"Service user '{user_name}' is not a member of any groups.")
            return

        printer.print(groups, [("uuid", "UUID"), ("name", "NAME")])

    finally:
        client.close()
