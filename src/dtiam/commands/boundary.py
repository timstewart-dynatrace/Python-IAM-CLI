"""Boundary management commands."""

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


@app.command("attach")
def attach_boundary(
    group: str = typer.Option(..., "--group", "-g", help="Group UUID or name"),
    policy: str = typer.Option(..., "--policy", "-p", help="Policy UUID or name"),
    boundary: str = typer.Option(..., "--boundary", "-b", help="Boundary UUID or name"),
) -> None:
    """Attach a boundary to an existing binding.

    Adds a boundary to restrict the scope of a policy binding.

    Example:
        dtiam boundary attach --group "DevOps" --policy "admin-policy" --boundary "prod-boundary"
    """
    from dtiam.resources.groups import GroupHandler
    from dtiam.resources.policies import PolicyHandler
    from dtiam.resources.boundaries import BoundaryHandler
    from dtiam.resources.bindings import BindingHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    group_handler = GroupHandler(client)
    policy_handler = PolicyHandler(client, level_type="account", level_id=client.account_uuid)
    boundary_handler = BoundaryHandler(client)
    binding_handler = BindingHandler(client)

    try:
        # Resolve group
        group_obj = group_handler.get(group)
        if not group_obj:
            group_obj = group_handler.get_by_name(group)

        if not group_obj:
            console.print(f"[red]Error:[/red] Group '{group}' not found.")
            raise typer.Exit(1)

        group_uuid = group_obj.get("uuid", "")
        group_name = group_obj.get("name", "")

        # Resolve policy
        policy_obj = policy_handler.get(policy)
        if not policy_obj:
            policy_obj = policy_handler.get_by_name(policy)

        if not policy_obj:
            console.print(f"[red]Error:[/red] Policy '{policy}' not found.")
            raise typer.Exit(1)

        policy_uuid = policy_obj.get("uuid", "")
        policy_name = policy_obj.get("name", "")

        # Resolve boundary
        boundary_obj = boundary_handler.get(boundary)
        if not boundary_obj:
            boundary_obj = boundary_handler.get_by_name(boundary)

        if not boundary_obj:
            console.print(f"[red]Error:[/red] Boundary '{boundary}' not found.")
            raise typer.Exit(1)

        boundary_uuid = boundary_obj.get("uuid", "")
        boundary_name = boundary_obj.get("name", "")

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would attach boundary '{boundary_name}'")
            console.print(f"  To binding: Group '{group_name}' -> Policy '{policy_name}'")
            return

        success = binding_handler.add_boundary(group_uuid, policy_uuid, boundary_uuid)

        if success:
            console.print(f"[green]Attached boundary:[/green] {boundary_name}")
            console.print(f"  To binding: {group_name} -> {policy_name}")
        else:
            console.print(f"[red]Error:[/red] Failed to attach boundary. Binding may not exist.")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("detach")
def detach_boundary(
    group: str = typer.Option(..., "--group", "-g", help="Group UUID or name"),
    policy: str = typer.Option(..., "--policy", "-p", help="Policy UUID or name"),
    boundary: str = typer.Option(..., "--boundary", "-b", help="Boundary UUID or name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Detach a boundary from a binding.

    Removes a boundary restriction from a policy binding.

    Example:
        dtiam boundary detach --group "DevOps" --policy "admin-policy" --boundary "prod-boundary"
    """
    from dtiam.resources.groups import GroupHandler
    from dtiam.resources.policies import PolicyHandler
    from dtiam.resources.boundaries import BoundaryHandler
    from dtiam.resources.bindings import BindingHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    group_handler = GroupHandler(client)
    policy_handler = PolicyHandler(client, level_type="account", level_id=client.account_uuid)
    boundary_handler = BoundaryHandler(client)
    binding_handler = BindingHandler(client)

    try:
        # Resolve group
        group_obj = group_handler.get(group)
        if not group_obj:
            group_obj = group_handler.get_by_name(group)

        if not group_obj:
            console.print(f"[red]Error:[/red] Group '{group}' not found.")
            raise typer.Exit(1)

        group_uuid = group_obj.get("uuid", "")
        group_name = group_obj.get("name", "")

        # Resolve policy
        policy_obj = policy_handler.get(policy)
        if not policy_obj:
            policy_obj = policy_handler.get_by_name(policy)

        if not policy_obj:
            console.print(f"[red]Error:[/red] Policy '{policy}' not found.")
            raise typer.Exit(1)

        policy_uuid = policy_obj.get("uuid", "")
        policy_name = policy_obj.get("name", "")

        # Resolve boundary
        boundary_obj = boundary_handler.get(boundary)
        if not boundary_obj:
            boundary_obj = boundary_handler.get_by_name(boundary)

        if not boundary_obj:
            console.print(f"[red]Error:[/red] Boundary '{boundary}' not found.")
            raise typer.Exit(1)

        boundary_uuid = boundary_obj.get("uuid", "")
        boundary_name = boundary_obj.get("name", "")

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would detach boundary '{boundary_name}'")
            console.print(f"  From binding: Group '{group_name}' -> Policy '{policy_name}'")
            return

        if not force:
            confirm = typer.confirm(
                f"Detach boundary '{boundary_name}' from binding '{group_name}' -> '{policy_name}'?"
            )
            if not confirm:
                console.print("Aborted.")
                raise typer.Exit(0)

        success = binding_handler.remove_boundary(group_uuid, policy_uuid, boundary_uuid)

        if success:
            console.print(f"[green]Detached boundary:[/green] {boundary_name}")
            console.print(f"  From binding: {group_name} -> {policy_name}")
        else:
            console.print(f"[red]Error:[/red] Failed to detach boundary.")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("list-attached")
def list_attached(
    boundary: str = typer.Argument(..., help="Boundary UUID or name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List all bindings that use a boundary."""
    from dtiam.resources.boundaries import BoundaryHandler
    from dtiam.resources.policies import PolicyHandler
    from dtiam.resources.groups import GroupHandler
    from dtiam.output import Printer

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    boundary_handler = BoundaryHandler(client)
    policy_handler = PolicyHandler(client, level_type="account", level_id=client.account_uuid)
    group_handler = GroupHandler(client)

    from dtiam.cli import state
    fmt = output or state.output
    printer = Printer(format=fmt, plain=state.plain)

    try:
        # Resolve boundary
        boundary_obj = boundary_handler.get(boundary)
        if not boundary_obj:
            boundary_obj = boundary_handler.get_by_name(boundary)

        if not boundary_obj:
            console.print(f"[red]Error:[/red] Boundary '{boundary}' not found.")
            raise typer.Exit(1)

        boundary_uuid = boundary_obj.get("uuid", "")
        boundary_name = boundary_obj.get("name", "")

        # Get attached policies
        attached = boundary_handler.get_attached_policies(boundary_uuid)

        # Enrich with names
        enriched = []
        for item in attached:
            policy_uuid = item.get("policyUuid", "")
            policy = policy_handler.get(policy_uuid)
            policy_name = policy.get("name", "") if policy else ""

            groups = item.get("groups", [])
            group_names = []
            for g_uuid in groups:
                group = group_handler.get(g_uuid)
                if group:
                    group_names.append(group.get("name", ""))

            enriched.append({
                "policy_uuid": policy_uuid,
                "policy_name": policy_name,
                "groups": group_names,
            })

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            printer.print({
                "boundary": {"uuid": boundary_uuid, "name": boundary_name},
                "attached": enriched,
            })
            return

        console.print(f"\n[bold]Bindings using boundary: {boundary_name}[/bold]\n")

        if not enriched:
            console.print("[yellow]No bindings found.[/yellow]")
            return

        from rich.table import Table
        table = Table(show_header=True)
        table.add_column("Policy")
        table.add_column("Groups")

        for item in enriched:
            groups_str = ", ".join(item["groups"]) if item["groups"] else "-"
            table.add_row(item["policy_name"], groups_str)

        console.print(table)

    finally:
        client.close()
