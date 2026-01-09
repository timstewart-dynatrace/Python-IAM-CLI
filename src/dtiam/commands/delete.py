"""Delete command for removing IAM resources."""

from __future__ import annotations

from typing import Optional

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


@app.command("group")
def delete_group(
    identifier: str = typer.Argument(..., help="Group UUID or name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete an IAM group."""
    from dtiam.resources.groups import GroupHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
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
    client = create_client_from_config(config, get_context(), is_verbose())

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
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = BindingHandler(client)

    try:
        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would delete binding:")
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
    client = create_client_from_config(config, get_context(), is_verbose())
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
