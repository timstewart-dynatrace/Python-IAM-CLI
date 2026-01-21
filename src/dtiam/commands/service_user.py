"""Service user management commands for IAM operations.

Advanced operations for service users (OAuth clients):
- update: Update service user name/description
- add-to-group: Add service user to a group
- remove-from-group: Remove service user from a group
- list-groups: List groups a service user belongs to

For basic operations use:
- dtiam get service-users
- dtiam create service-user
- dtiam delete service-user
"""

from __future__ import annotations

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


@app.command("update")
def update_service_user(
    user: str = typer.Argument(..., help="Service user UUID or name"),
    name: str = typer.Option("", "--name", "-n", help="New name"),
    description: str = typer.Option("", "--description", "-d", help="New description"),
    output: OutputFormat | None = typer.Option(None, "-o", "--output"),
) -> None:
    """Update a service user.

    Example:
        dtiam service-user update my-service-user --name "New Name"
        dtiam service-user update my-service-user --description "Updated description"
    """
    from dtiam.resources.service_users import ServiceUserHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
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


@app.command("add-to-group")
def add_to_group(
    user: str = typer.Option(..., "--user", "-u", help="Service user UUID or name"),
    group: str = typer.Option(..., "--group", "-g", help="Group UUID or name"),
) -> None:
    """Add a service user to a group.

    Example:
        dtiam service-user add-to-group --user my-service-user --group DevOps
    """
    from dtiam.resources.groups import GroupHandler
    from dtiam.resources.service_users import ServiceUserHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
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
            console.print("[red]Error:[/red] Failed to add service user to group")
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
    from dtiam.resources.groups import GroupHandler
    from dtiam.resources.service_users import ServiceUserHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
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
            console.print("[red]Error:[/red] Failed to remove service user from group")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("list-groups")
def list_groups(
    user: str = typer.Argument(..., help="Service user UUID or name"),
    output: OutputFormat | None = typer.Option(None, "-o", "--output"),
) -> None:
    """List all groups a service user belongs to.

    Example:
        dtiam service-user list-groups my-service-user
    """
    from dtiam.resources.service_users import ServiceUserHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
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
