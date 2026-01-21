"""User management commands for IAM operations."""

from __future__ import annotations

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


def get_api_url() -> str | None:
    """Get API URL override from CLI state."""
    from dtiam.cli import state
    return state.api_url


@app.command("create")
def create_user(
    email: str = typer.Option(..., "--email", "-e", help="User email address"),
    first_name: str = typer.Option("", "--first-name", "-f", help="User's first name"),
    last_name: str = typer.Option("", "--last-name", "-l", help="User's last name"),
    groups: str = typer.Option("", "--groups", "-g", help="Comma-separated group UUIDs or names"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Create a new user in the account.

    Creates a user with the specified email and optionally adds them to groups.

    Example:
        dtiam user create --email user@example.com
        dtiam user create --email user@example.com --first-name John --last-name Doe
        dtiam user create --email user@example.com --groups "DevOps,Platform"
    """
    from dtiam.resources.users import UserHandler
    from dtiam.resources.groups import GroupHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    user_handler = UserHandler(client)

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

                # Try as UUID first, then by name
                group_obj = group_handler.get(group_ref)
                if not group_obj:
                    group_obj = group_handler.get_by_name(group_ref)

                if group_obj:
                    group_uuids.append(group_obj.get("uuid", ""))
                else:
                    console.print(f"[yellow]Warning:[/yellow] Group '{group_ref}' not found, skipping.")

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would create user '{email}'")
            if first_name or last_name:
                console.print(f"  Name: {first_name} {last_name}")
            if group_uuids:
                console.print(f"  Groups: {len(group_uuids)} groups")
            return

        result = user_handler.create(
            email=email,
            first_name=first_name if first_name else None,
            last_name=last_name if last_name else None,
            groups=group_uuids if group_uuids else None,
        )

        if result:
            console.print(f"[green]Created user:[/green] {email}")
            printer.print(result)
        else:
            console.print(f"[red]Error:[/red] Failed to create user '{email}'")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("delete")
def delete_user(
    user: str = typer.Argument(..., help="User email or UID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a user from the account.

    Example:
        dtiam user delete user@example.com
        dtiam user delete user@example.com --force
    """
    from dtiam.resources.users import UserHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = UserHandler(client)

    try:
        # Resolve user by email or UID
        if "@" in user:
            user_obj = handler.get_by_email(user)
        else:
            user_obj = handler.get(user)

        if not user_obj:
            console.print(f"[red]Error:[/red] User '{user}' not found.")
            raise typer.Exit(1)

        user_id = user_obj.get("uid", "")
        user_email = user_obj.get("email", user)

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would delete user '{user_email}'")
            return

        if not force:
            confirm = typer.confirm(f"Delete user '{user_email}'? This cannot be undone.")
            if not confirm:
                console.print("Aborted.")
                raise typer.Exit(0)

        success = handler.delete(user_id)

        if success:
            console.print(f"[green]Deleted user:[/green] {user_email}")
        else:
            console.print(f"[red]Error:[/red] Failed to delete user '{user_email}'")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("add-to-group")
def add_user_to_group(
    user: str = typer.Option(..., "--user", "-u", help="User email address"),
    group: str = typer.Option(..., "--group", "-g", help="Group UUID or name"),
) -> None:
    """Add a user to an IAM group."""
    from dtiam.resources.groups import GroupHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = GroupHandler(client)

    try:
        # Resolve group by UUID or name
        group_obj = handler.get(group)
        if not group_obj:
            group_obj = handler.get_by_name(group)
        if not group_obj:
            console.print(f"[red]Error:[/red] Group '{group}' not found.")
            raise typer.Exit(1)

        group_id = group_obj.get("uuid")
        group_name = group_obj.get("name", group)

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would add user '{user}' to group '{group_name}'")
            return

        success = handler.add_member(group_id, user)
        if success:
            console.print(f"[green]Added user[/green] '{user}' to group '{group_name}'")
        else:
            console.print(f"[red]Error:[/red] Failed to add user '{user}' to group '{group_name}'")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("remove-from-group")
def remove_user_from_group(
    user: str = typer.Option(..., "--user", "-u", help="User email or UID"),
    group: str = typer.Option(..., "--group", "-g", help="Group UUID or name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Remove a user from an IAM group."""
    from dtiam.resources.groups import GroupHandler
    from dtiam.resources.users import UserHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    group_handler = GroupHandler(client)
    user_handler = UserHandler(client)

    try:
        # Resolve group by UUID or name
        group_obj = group_handler.get(group)
        if not group_obj:
            group_obj = group_handler.get_by_name(group)
        if not group_obj:
            console.print(f"[red]Error:[/red] Group '{group}' not found.")
            raise typer.Exit(1)

        group_id = group_obj.get("uuid")
        group_name = group_obj.get("name", group)

        # Resolve user - if email, get UID
        user_id = user
        user_display = user
        if "@" in user:
            user_obj = user_handler.get_by_email(user)
            if not user_obj:
                console.print(f"[red]Error:[/red] User '{user}' not found.")
                raise typer.Exit(1)
            user_id = user_obj.get("uid", user)
            user_display = user_obj.get("email", user)

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would remove user '{user_display}' from group '{group_name}'")
            return

        if not force:
            confirm = typer.confirm(f"Remove user '{user_display}' from group '{group_name}'?")
            if not confirm:
                console.print("Aborted.")
                raise typer.Exit(0)

        success = group_handler.remove_member(group_id, user_id)
        if success:
            console.print(f"[green]Removed user[/green] '{user_display}' from group '{group_name}'")
        else:
            console.print(f"[red]Error:[/red] Failed to remove user '{user_display}' from group '{group_name}'")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("list-groups")
def list_user_groups(
    user: str = typer.Argument(..., help="User email or UID"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List all groups a user belongs to."""
    from dtiam.resources.users import UserHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = UserHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        # Resolve user by UID or email
        if "@" in user:
            user_obj = handler.get_by_email(user)
        else:
            user_obj = handler.get(user)

        if not user_obj:
            console.print(f"[red]Error:[/red] User '{user}' not found.")
            raise typer.Exit(1)

        user_id = user_obj.get("uid")
        groups = handler.get_groups(user_id)

        if not groups:
            console.print(f"User '{user}' is not a member of any groups.")
            return

        printer.print(groups, [("uuid", "UUID"), ("name", "Name")])

    finally:
        client.close()


@app.command("info")
def user_info(
    user: str = typer.Argument(..., help="User email or UID"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Show detailed information about a user."""
    from dtiam.resources.users import UserHandler
    from dtiam.commands.describe import print_detail_view

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = UserHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        # Resolve user by UID or email
        if "@" in user:
            user_obj = handler.get_by_email(user)
        else:
            user_obj = handler.get(user)

        if not user_obj:
            console.print(f"[red]Error:[/red] User '{user}' not found.")
            raise typer.Exit(1)

        # Get expanded details
        user_id = user_obj.get("uid")
        result = handler.get_expanded(user_id)

        if output:
            printer.print(result)
        else:
            print_detail_view(result, f"User: {result.get('email', user)}")

    finally:
        client.close()


@app.command("replace-groups")
def replace_user_groups(
    user: str = typer.Option(..., "--user", "-u", help="User email address"),
    groups: str = typer.Option(..., "--groups", "-g", help="Comma-separated group UUIDs or names"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Replace all group memberships for a user.

    This will remove the user from all current groups and add them to the specified groups.

    Example:
        dtiam user replace-groups --user user@example.com --groups "DevOps,Platform"
    """
    from dtiam.resources.users import UserHandler
    from dtiam.resources.groups import GroupHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    user_handler = UserHandler(client)
    group_handler = GroupHandler(client)

    try:
        # Resolve groups
        group_uuids: list[str] = []
        group_names: list[str] = []
        for group_ref in groups.split(","):
            group_ref = group_ref.strip()
            if not group_ref:
                continue

            group_obj = group_handler.get(group_ref)
            if not group_obj:
                group_obj = group_handler.get_by_name(group_ref)

            if group_obj:
                group_uuids.append(group_obj.get("uuid", ""))
                group_names.append(group_obj.get("name", group_ref))
            else:
                console.print(f"[yellow]Warning:[/yellow] Group '{group_ref}' not found, skipping.")

        if not group_uuids:
            console.print("[red]Error:[/red] No valid groups specified.")
            raise typer.Exit(1)

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would replace groups for user '{user}'")
            console.print(f"  New groups: {', '.join(group_names)}")
            return

        if not force:
            confirm = typer.confirm(
                f"Replace all group memberships for '{user}' with: {', '.join(group_names)}?"
            )
            if not confirm:
                console.print("Aborted.")
                raise typer.Exit(0)

        success = user_handler.replace_groups(user, group_uuids)

        if success:
            console.print(f"[green]Replaced groups for user:[/green] {user}")
            console.print(f"  New groups: {', '.join(group_names)}")
        else:
            console.print(f"[red]Error:[/red] Failed to replace groups for user '{user}'")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("bulk-remove-groups")
def bulk_remove_user_from_groups(
    user: str = typer.Option(..., "--user", "-u", help="User email address"),
    groups: str = typer.Option(..., "--groups", "-g", help="Comma-separated group UUIDs or names"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Remove a user from multiple groups at once.

    Example:
        dtiam user bulk-remove-groups --user user@example.com --groups "DevOps,Platform"
    """
    from dtiam.resources.users import UserHandler
    from dtiam.resources.groups import GroupHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    user_handler = UserHandler(client)
    group_handler = GroupHandler(client)

    try:
        # Resolve groups
        group_uuids: list[str] = []
        group_names: list[str] = []
        for group_ref in groups.split(","):
            group_ref = group_ref.strip()
            if not group_ref:
                continue

            group_obj = group_handler.get(group_ref)
            if not group_obj:
                group_obj = group_handler.get_by_name(group_ref)

            if group_obj:
                group_uuids.append(group_obj.get("uuid", ""))
                group_names.append(group_obj.get("name", group_ref))
            else:
                console.print(f"[yellow]Warning:[/yellow] Group '{group_ref}' not found, skipping.")

        if not group_uuids:
            console.print("[red]Error:[/red] No valid groups specified.")
            raise typer.Exit(1)

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would remove user '{user}' from groups")
            console.print(f"  Groups: {', '.join(group_names)}")
            return

        if not force:
            confirm = typer.confirm(
                f"Remove '{user}' from groups: {', '.join(group_names)}?"
            )
            if not confirm:
                console.print("Aborted.")
                raise typer.Exit(0)

        success = user_handler.remove_from_groups(user, group_uuids)

        if success:
            console.print(f"[green]Removed user from groups:[/green] {user}")
            console.print(f"  Removed from: {', '.join(group_names)}")
        else:
            console.print(f"[red]Error:[/red] Failed to remove user from groups")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("bulk-add-groups")
def bulk_add_user_to_groups(
    user: str = typer.Option(..., "--user", "-u", help="User email address"),
    groups: str = typer.Option(..., "--groups", "-g", help="Comma-separated group UUIDs or names"),
) -> None:
    """Add a user to multiple groups at once.

    Example:
        dtiam user bulk-add-groups --user user@example.com --groups "DevOps,Platform"
    """
    from dtiam.resources.users import UserHandler
    from dtiam.resources.groups import GroupHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    user_handler = UserHandler(client)
    group_handler = GroupHandler(client)

    try:
        # Resolve groups
        group_uuids: list[str] = []
        group_names: list[str] = []
        for group_ref in groups.split(","):
            group_ref = group_ref.strip()
            if not group_ref:
                continue

            group_obj = group_handler.get(group_ref)
            if not group_obj:
                group_obj = group_handler.get_by_name(group_ref)

            if group_obj:
                group_uuids.append(group_obj.get("uuid", ""))
                group_names.append(group_obj.get("name", group_ref))
            else:
                console.print(f"[yellow]Warning:[/yellow] Group '{group_ref}' not found, skipping.")

        if not group_uuids:
            console.print("[red]Error:[/red] No valid groups specified.")
            raise typer.Exit(1)

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would add user '{user}' to groups")
            console.print(f"  Groups: {', '.join(group_names)}")
            return

        success = user_handler.add_to_groups(user, group_uuids)

        if success:
            console.print(f"[green]Added user to groups:[/green] {user}")
            console.print(f"  Added to: {', '.join(group_names)}")
        else:
            console.print(f"[red]Error:[/red] Failed to add user to groups")
            raise typer.Exit(1)

    finally:
        client.close()
