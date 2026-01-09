"""Advanced group management commands."""

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


@app.command("clone")
def clone_group(
    source: str = typer.Argument(..., help="Source group UUID or name"),
    new_name: str = typer.Option(..., "--name", "-n", help="Name for the cloned group"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description (uses source if not provided)"),
    include_members: bool = typer.Option(False, "--include-members", "-m", help="Copy members to new group"),
    include_policies: bool = typer.Option(True, "--include-policies/--no-policies", help="Copy policy bindings"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Clone an existing group with its configuration.

    Creates a new group based on an existing one, optionally copying
    members and policy bindings.

    Example:
        dtiam group clone "Source Group" --name "New Group"
        dtiam group clone "Source Group" --name "New Group" --include-members
    """
    from dtiam.resources.groups import GroupHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = GroupHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        # Resolve source group
        source_group = handler.get(source)
        if not source_group:
            source_group = handler.get_by_name(source)

        if not source_group:
            console.print(f"[red]Error:[/red] Source group '{source}' not found.")
            raise typer.Exit(1)

        source_id = source_group.get("uuid", "")
        source_name = source_group.get("name", "")

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would clone group '{source_name}' to '{new_name}'")
            console.print(f"  Include members: {include_members}")
            console.print(f"  Include policies: {include_policies}")
            return

        result = handler.clone(
            source_group_id=source_id,
            new_name=new_name,
            new_description=description,
            include_members=include_members,
            include_policies=include_policies,
        )

        console.print(f"[green]Cloned group:[/green] '{source_name}' -> '{new_name}'")
        printer.print(result)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    finally:
        client.close()


@app.command("setup")
def setup_group(
    name: str = typer.Option(..., "--name", "-n", help="Group name"),
    policy: str = typer.Option(..., "--policy", "-p", help="Policy UUID or name to bind"),
    boundary: Optional[str] = typer.Option(None, "--boundary", "-b", help="Boundary UUID or name"),
    description: str = typer.Option("", "--description", "-d", help="Group description"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Create a group with policy binding in one command.

    This is a convenience command that creates a group and binds a policy
    to it in a single operation.

    Example:
        dtiam group setup --name "DevOps Team" --policy "devops-policy"
        dtiam group setup --name "Prod Team" --policy "prod-policy" --boundary "prod-boundary"
    """
    from dtiam.resources.groups import GroupHandler
    from dtiam.resources.policies import PolicyHandler
    from dtiam.resources.boundaries import BoundaryHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    group_handler = GroupHandler(client)
    policy_handler = PolicyHandler(client, level_type="account", level_id=client.account_uuid)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        # Resolve policy
        policy_obj = policy_handler.get(policy)
        if not policy_obj:
            policy_obj = policy_handler.get_by_name(policy)

        if not policy_obj:
            console.print(f"[red]Error:[/red] Policy '{policy}' not found.")
            raise typer.Exit(1)

        policy_uuid = policy_obj.get("uuid", "")
        policy_name = policy_obj.get("name", "")

        # Resolve boundary if provided
        boundary_uuid = None
        if boundary:
            boundary_handler = BoundaryHandler(client)
            boundary_obj = boundary_handler.get(boundary)
            if not boundary_obj:
                boundary_obj = boundary_handler.get_by_name(boundary)

            if not boundary_obj:
                console.print(f"[red]Error:[/red] Boundary '{boundary}' not found.")
                raise typer.Exit(1)

            boundary_uuid = boundary_obj.get("uuid", "")

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would create group '{name}'")
            console.print(f"  Policy: {policy_name}")
            if boundary_uuid:
                console.print(f"  Boundary: {boundary}")
            return

        result = group_handler.setup_with_policy(
            group_name=name,
            policy_uuid=policy_uuid,
            boundary_uuid=boundary_uuid,
            description=description,
        )

        console.print(f"[green]Created group:[/green] {name}")
        console.print(f"[green]Bound policy:[/green] {policy_name}")
        if boundary_uuid:
            console.print(f"[green]Applied boundary:[/green] {boundary}")

        printer.print(result["group"])

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    finally:
        client.close()


@app.command("list-bindings")
def list_group_bindings(
    group: str = typer.Argument(..., help="Group UUID or name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List all policy bindings for a group.

    Shows which policies are bound to the group and any boundaries applied.
    """
    from dtiam.resources.groups import GroupHandler
    from dtiam.resources.bindings import BindingHandler
    from dtiam.resources.policies import PolicyHandler
    from dtiam.resources.boundaries import BoundaryHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    group_handler = GroupHandler(client)
    binding_handler = BindingHandler(client)
    policy_handler = PolicyHandler(client, level_type="account", level_id=client.account_uuid)
    boundary_handler = BoundaryHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

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

        # Get bindings
        bindings = binding_handler.get_for_group(group_uuid)

        # Enrich with names
        enriched = []
        for binding in bindings:
            policy_uuid = binding.get("policyUuid", "")
            boundary_uuid = binding.get("boundaryUuid")

            policy = policy_handler.get(policy_uuid)
            policy_name = policy.get("name", "") if policy else ""

            boundary_name = ""
            if boundary_uuid:
                boundary = boundary_handler.get(boundary_uuid)
                boundary_name = boundary.get("name", "") if boundary else ""

            enriched.append({
                "policy_uuid": policy_uuid,
                "policy_name": policy_name,
                "boundary_uuid": boundary_uuid or "",
                "boundary_name": boundary_name,
            })

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            printer.print({
                "group": {"uuid": group_uuid, "name": group_name},
                "bindings": enriched,
            })
            return

        # Table output
        console.print(f"\n[bold]Bindings for group: {group_name}[/bold]\n")

        if not enriched:
            console.print("[yellow]No bindings found.[/yellow]")
            return

        from rich.table import Table
        table = Table(show_header=True)
        table.add_column("Policy")
        table.add_column("Boundary")

        for b in enriched:
            boundary_str = b["boundary_name"] or "-"
            table.add_row(b["policy_name"], boundary_str)

        console.print(table)

    finally:
        client.close()


@app.command("list-members")
def list_group_members(
    group: str = typer.Argument(..., help="Group UUID or name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List all members of a group."""
    from dtiam.resources.groups import GroupHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = GroupHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        # Resolve group
        group_obj = handler.get(group)
        if not group_obj:
            group_obj = handler.get_by_name(group)

        if not group_obj:
            console.print(f"[red]Error:[/red] Group '{group}' not found.")
            raise typer.Exit(1)

        group_uuid = group_obj.get("uuid", "")
        group_name = group_obj.get("name", "")

        members = handler.get_members(group_uuid)

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            printer.print({
                "group": {"uuid": group_uuid, "name": group_name},
                "members": members,
                "member_count": len(members),
            })
            return

        console.print(f"\n[bold]Members of group: {group_name}[/bold] ({len(members)} total)\n")

        if not members:
            console.print("[yellow]No members found.[/yellow]")
            return

        columns = [("email", "Email"), ("uid", "UID")]
        printer.print(members, columns)

    finally:
        client.close()
