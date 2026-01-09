"""Describe command for showing detailed resource information."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import yaml

from dtiam.client import create_client_from_config
from dtiam.config import load_config
from dtiam.output import OutputFormat, Printer

app = typer.Typer(no_args_is_help=True)
console = Console()


def get_output_format() -> OutputFormat:
    """Get output format from CLI state."""
    from dtiam.cli import state
    return state.output


def is_plain_mode() -> bool:
    """Check if plain mode is enabled."""
    from dtiam.cli import state
    return state.plain


def get_context() -> str | None:
    """Get context override from CLI state."""
    from dtiam.cli import state
    return state.context


def is_verbose() -> bool:
    """Check if verbose mode is enabled."""
    from dtiam.cli import state
    return state.verbose


def print_detail_view(data: dict, title: str) -> None:
    """Print a detailed view of a resource."""
    fmt = get_output_format()

    if fmt in (OutputFormat.JSON, OutputFormat.YAML, OutputFormat.PLAIN):
        printer = Printer(format=fmt, plain=is_plain_mode())
        printer.print(data)
        return

    # Default: formatted panel view
    console.print()
    console.print(Panel(f"[bold]{title}[/bold]"))

    # Print main attributes
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    # Define key order for common fields
    priority_keys = ["uuid", "name", "email", "description", "owner", "createdAt", "userStatus"]
    seen_keys = set()

    for key in priority_keys:
        if key in data:
            value = data[key]
            if value is not None:
                table.add_row(key, str(value))
                seen_keys.add(key)

    # Add remaining keys
    for key, value in data.items():
        if key not in seen_keys and not key.startswith("_"):
            if isinstance(value, (list, dict)):
                continue  # Handle complex types separately
            if value is not None:
                table.add_row(key, str(value))

    console.print(table)

    # Handle nested data (members, policies, etc.)
    for key, value in data.items():
        if isinstance(value, list) and value:
            console.print()
            console.print(f"[bold]{key.title()}:[/bold] ({len(value)} items)")
            if isinstance(value[0], dict):
                # Print as mini-table
                sub_table = Table(show_header=True, header_style="dim")
                headers = list(value[0].keys())[:4]  # Limit columns
                for h in headers:
                    sub_table.add_column(h)
                for item in value[:10]:  # Limit rows
                    row = [str(item.get(h, ""))[:50] for h in headers]
                    sub_table.add_row(*row)
                if len(value) > 10:
                    console.print(f"  ... and {len(value) - 10} more")
                console.print(sub_table)
            else:
                # Simple list
                for item in value[:10]:
                    console.print(f"  - {item}")
                if len(value) > 10:
                    console.print(f"  ... and {len(value) - 10} more")

    console.print()


@app.command("group")
def describe_group(
    identifier: str = typer.Argument(..., help="Group UUID or name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Show detailed information about an IAM group."""
    from dtiam.resources.groups import GroupHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = GroupHandler(client)

    try:
        # Try to resolve by UUID or name
        result = handler.get(identifier)
        if not result:
            result = handler.get_by_name(identifier)
        if not result:
            console.print(f"[red]Error:[/red] Group '{identifier}' not found.")
            raise typer.Exit(1)

        # Get expanded details
        group_id = result.get("uuid")
        result = handler.get_expanded(group_id)

        if output:
            printer = Printer(format=output, plain=is_plain_mode())
            printer.print(result)
        else:
            print_detail_view(result, f"Group: {result.get('name', identifier)}")
    finally:
        client.close()


@app.command("user")
def describe_user(
    identifier: str = typer.Argument(..., help="User UID or email"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Show detailed information about an IAM user."""
    from dtiam.resources.users import UserHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = UserHandler(client)

    try:
        # Try to resolve by UID or email
        result = handler.get(identifier)
        if not result:
            result = handler.get_by_email(identifier)
        if not result:
            console.print(f"[red]Error:[/red] User '{identifier}' not found.")
            raise typer.Exit(1)

        # Get expanded details
        user_id = result.get("uid")
        result = handler.get_expanded(user_id)

        if output:
            printer = Printer(format=output, plain=is_plain_mode())
            printer.print(result)
        else:
            print_detail_view(result, f"User: {result.get('email', identifier)}")
    finally:
        client.close()


@app.command("policy")
def describe_policy(
    identifier: str = typer.Argument(..., help="Policy UUID or name"),
    level: str = typer.Option("account", "--level", "-l", help="Policy level (account, global)"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Show detailed information about an IAM policy."""
    from dtiam.resources.policies import PolicyHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    level_type = "global" if level == "global" else "account"
    level_id = "global" if level == "global" else client.account_uuid

    handler = PolicyHandler(client, level_type=level_type, level_id=level_id)

    try:
        # Try to resolve by UUID or name
        result = handler.get(identifier)
        if not result:
            result = handler.get_by_name(identifier)
        if not result:
            console.print(f"[red]Error:[/red] Policy '{identifier}' not found.")
            raise typer.Exit(1)

        if output:
            printer = Printer(format=output, plain=is_plain_mode())
            printer.print(result)
        else:
            print_detail_view(result, f"Policy: {result.get('name', identifier)}")

            # Show statement query if present
            statement = result.get("statementQuery")
            if statement:
                console.print("[bold]Statement Query:[/bold]")
                console.print(Panel(statement, expand=False))
    finally:
        client.close()


@app.command("environment")
@app.command("env")
def describe_environment(
    identifier: str = typer.Argument(..., help="Environment ID or name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Show detailed information about a Dynatrace environment."""
    from dtiam.resources.environments import EnvironmentHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = EnvironmentHandler(client)

    try:
        # Try to resolve by ID or name
        result = handler.get(identifier)
        if not result:
            result = handler.get_by_name(identifier)
        if not result:
            console.print(f"[red]Error:[/red] Environment '{identifier}' not found.")
            raise typer.Exit(1)

        if output:
            printer = Printer(format=output, plain=is_plain_mode())
            printer.print(result)
        else:
            print_detail_view(result, f"Environment: {result.get('name', identifier)}")
    finally:
        client.close()


@app.command("boundary")
def describe_boundary(
    identifier: str = typer.Argument(..., help="Boundary UUID or name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Show detailed information about an IAM policy boundary."""
    from dtiam.resources.boundaries import BoundaryHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = BoundaryHandler(client)

    try:
        # Try to resolve by UUID or name
        result = handler.get(identifier)
        if not result:
            result = handler.get_by_name(identifier)
        if not result:
            console.print(f"[red]Error:[/red] Boundary '{identifier}' not found.")
            raise typer.Exit(1)

        # Get attached policies
        boundary_id = result.get("uuid")
        attached = handler.get_attached_policies(boundary_id)
        result["attached_policies"] = attached
        result["attached_policy_count"] = len(attached)

        if output:
            printer = Printer(format=output, plain=is_plain_mode())
            printer.print(result)
        else:
            print_detail_view(result, f"Boundary: {result.get('name', identifier)}")

            # Show boundary query if present
            query = result.get("boundaryQuery")
            if query:
                console.print("[bold]Boundary Query:[/bold]")
                console.print(Panel(query, expand=False))
    finally:
        client.close()
