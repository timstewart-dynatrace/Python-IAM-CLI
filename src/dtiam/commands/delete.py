"""Delete command for removing IAM resources."""

from __future__ import annotations

import typer
from rich.console import Console

from dtiam.client import create_client_from_config
from dtiam.config import load_config

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


def get_api_url() -> str | None:
    """Get API URL override from CLI state."""
    from dtiam.cli import state
    return state.api_url


@app.command("group")
def delete_group(
    identifier: str = typer.Argument(..., help="Group UUID or name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete an IAM group."""
    from dtiam.resources.groups import GroupHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = GroupHandler(client)

    try:
        # Resolve by UUID or name
        group = handler.get(identifier)
        if not group:
            group = handler.get_by_name(identifier)
        if not group:
            console.print(f"[red]Error:[/red] Group '{identifier}' not found.")
            raise typer.Exit(1)

        group_id = group.get("uuid")
        group_name = group.get("name", identifier)

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would delete group: {group_name} ({group_id})")
            return

        if not force:
            confirm = typer.confirm(f"Delete group '{group_name}'?")
            if not confirm:
                console.print("Aborted.")
                raise typer.Exit(0)

        success = handler.delete(group_id)
        if success:
            console.print(f"[green]Deleted group:[/green] {group_name}")
        else:
            console.print(f"[red]Error:[/red] Failed to delete group '{group_name}'")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("policy")
def delete_policy(
    identifier: str = typer.Argument(..., help="Policy UUID or name"),
    level: str = typer.Option("account", "--level", "-l", help="Policy level (account)"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete an IAM policy."""
    from dtiam.resources.policies import PolicyHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())

    level_type = "account"  # Only account-level policies can be deleted
    level_id = client.account_uuid

    handler = PolicyHandler(client, level_type=level_type, level_id=level_id)

    try:
        # Resolve by UUID or name
        policy = handler.get(identifier)
        if not policy:
            policy = handler.get_by_name(identifier)
        if not policy:
            console.print(f"[red]Error:[/red] Policy '{identifier}' not found.")
            raise typer.Exit(1)

        policy_id = policy.get("uuid")
        policy_name = policy.get("name", identifier)

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would delete policy: {policy_name} ({policy_id})")
            return

        if not force:
            confirm = typer.confirm(f"Delete policy '{policy_name}'?")
            if not confirm:
                console.print("Aborted.")
                raise typer.Exit(0)

        success = handler.delete(policy_id)
        if success:
            console.print(f"[green]Deleted policy:[/green] {policy_name}")
        else:
            console.print(f"[red]Error:[/red] Failed to delete policy '{policy_name}'")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("binding")
def delete_binding(
    group: str = typer.Option(..., "--group", "-g", help="Group UUID"),
    policy: str = typer.Option(..., "--policy", "-p", help="Policy UUID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a policy binding (unbind a policy from a group)."""
    from dtiam.resources.bindings import BindingHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = BindingHandler(client)

    try:
        if is_dry_run():
            console.print("[yellow]Dry-run mode:[/yellow] Would delete binding:")
            console.print(f"  Group: {group}")
            console.print(f"  Policy: {policy}")
            return

        if not force:
            confirm = typer.confirm(f"Delete binding between group '{group}' and policy '{policy}'?")
            if not confirm:
                console.print("Aborted.")
                raise typer.Exit(0)

        success = handler.delete(group_uuid=group, policy_uuid=policy)
        if success:
            console.print("[green]Deleted binding[/green]")
        else:
            console.print("[red]Error:[/red] Failed to delete binding")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("boundary")
def delete_boundary(
    identifier: str = typer.Argument(..., help="Boundary UUID or name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete an IAM policy boundary."""
    from dtiam.resources.boundaries import BoundaryHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = BoundaryHandler(client)

    try:
        # Resolve by UUID or name
        boundary = handler.get(identifier)
        if not boundary:
            boundary = handler.get_by_name(identifier)
        if not boundary:
            console.print(f"[red]Error:[/red] Boundary '{identifier}' not found.")
            raise typer.Exit(1)

        boundary_id = boundary.get("uuid")
        boundary_name = boundary.get("name", identifier)

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would delete boundary: {boundary_name} ({boundary_id})")
            return

        if not force:
            confirm = typer.confirm(f"Delete boundary '{boundary_name}'?")
            if not confirm:
                console.print("Aborted.")
                raise typer.Exit(0)

        success = handler.delete(boundary_id)
        if success:
            console.print(f"[green]Deleted boundary:[/green] {boundary_name}")
        else:
            console.print(f"[red]Error:[/red] Failed to delete boundary '{boundary_name}'")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("service-user")
def delete_service_user(
    identifier: str = typer.Argument(..., help="Service user UUID or name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a service user (OAuth client).

    This will immediately revoke any OAuth tokens and applications
    using this service user will no longer be able to authenticate.

    Example:
        dtiam delete service-user my-service-user
        dtiam delete service-user my-service-user --force
    """
    from dtiam.resources.service_users import ServiceUserHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = ServiceUserHandler(client)

    try:
        # Resolve by UUID or name
        user = handler.get(identifier)
        if not user:
            user = handler.get_by_name(identifier)
        if not user:
            console.print(f"[red]Error:[/red] Service user '{identifier}' not found.")
            raise typer.Exit(1)

        user_id = user.get("uid")
        user_name = user.get("name", identifier)

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would delete service user: {user_name} ({user_id})")
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


@app.command("platform-token")
def delete_platform_token(
    identifier: str = typer.Argument(..., help="Platform token ID or name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a platform token.

    This will immediately revoke the token and any applications using it
    will no longer be able to authenticate.

    Requires the `platform-token:tokens:manage` scope.

    Example:
        dtiam delete platform-token abc-123-def
        dtiam delete platform-token "CI Pipeline Token"
        dtiam delete platform-token abc-123 --force
    """
    from dtiam.resources.platform_tokens import PlatformTokenHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = PlatformTokenHandler(client)

    try:
        # Resolve by ID or name
        token = handler.get(identifier)
        if not token:
            token = handler.get_by_name(identifier)
        if not token:
            console.print(f"[red]Error:[/red] Platform token '{identifier}' not found.")
            raise typer.Exit(1)

        token_id = token.get("id")
        token_name = token.get("name", identifier)

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would delete platform token: {token_name} ({token_id})")
            return

        if not force:
            confirm = typer.confirm(
                f"Delete platform token '{token_name}'? Applications using this token will lose access."
            )
            if not confirm:
                console.print("Aborted.")
                raise typer.Exit(0)

        success = handler.delete(token_id)
        if success:
            console.print(f"[green]Deleted platform token:[/green] {token_name}")
        else:
            console.print(f"[red]Error:[/red] Failed to delete platform token '{token_name}'")
            raise typer.Exit(1)

    finally:
        client.close()
