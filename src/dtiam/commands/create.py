"""Create command for creating IAM resources."""

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


@app.command("group")
def create_group(
    name: str = typer.Option(..., "--name", "-n", help="Group name"),
    description: str = typer.Option("", "--description", "-d", help="Group description"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Create a new IAM group."""
    from dtiam.resources.groups import GroupHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
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
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Create a new IAM policy."""
    from dtiam.resources.policies import PolicyHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

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
    boundary: Optional[str] = typer.Option(None, "--boundary", "-b", help="Boundary UUID"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Create a policy binding (bind a policy to a group)."""
    from dtiam.resources.bindings import BindingHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
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
    zones: Optional[str] = typer.Option(None, "--zones", "-z", help="Management zones (comma-separated)"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Custom boundary query"),
    description: str = typer.Option("", "--description", "-d", help="Boundary description"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
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
    client = create_client_from_config(config, get_context(), is_verbose())
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
