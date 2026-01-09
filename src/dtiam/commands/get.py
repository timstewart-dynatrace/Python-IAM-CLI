"""Get command for listing and retrieving IAM resources."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from dtiam.client import create_client_from_config
from dtiam.config import load_config
from dtiam.output import (
    Printer,
    OutputFormat,
    group_columns,
    user_columns,
    policy_columns,
    binding_columns,
    environment_columns,
    boundary_columns,
)

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


@app.command("groups")
@app.command("group")
def get_groups(
    identifier: Optional[str] = typer.Argument(None, help="Group UUID or name"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List or get IAM groups."""
    from dtiam.resources.groups import GroupHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = GroupHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        if identifier:
            # Try to resolve by UUID or name
            result = handler.get(identifier)
            if not result:
                result = handler.get_by_name(identifier)
            if not result:
                console.print(f"[red]Error:[/red] Group '{identifier}' not found.")
                raise typer.Exit(1)
            printer.print(result)
        else:
            # List groups
            results = handler.list()
            if name:
                results = [g for g in results if name.lower() in g.get("name", "").lower()]
            printer.print(results, group_columns())
    finally:
        client.close()


@app.command("users")
@app.command("user")
def get_users(
    identifier: Optional[str] = typer.Argument(None, help="User UID or email"),
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Filter by email"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List or get IAM users."""
    from dtiam.resources.users import UserHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = UserHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        if identifier:
            # Try to resolve by UID or email
            result = handler.get(identifier)
            if not result:
                result = handler.get_by_email(identifier)
            if not result:
                console.print(f"[red]Error:[/red] User '{identifier}' not found.")
                raise typer.Exit(1)
            printer.print(result)
        else:
            # List users
            results = handler.list()
            if email:
                results = [u for u in results if email.lower() in u.get("email", "").lower()]
            printer.print(results, user_columns())
    finally:
        client.close()


@app.command("policies")
@app.command("policy")
def get_policies(
    identifier: Optional[str] = typer.Argument(None, help="Policy UUID or name"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by name"),
    level: str = typer.Option("account", "--level", "-l", help="Policy level (account, global)"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List or get IAM policies."""
    from dtiam.resources.policies import PolicyHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    # Determine level type
    level_type = "global" if level == "global" else "account"
    level_id = "global" if level == "global" else client.account_uuid

    handler = PolicyHandler(client, level_type=level_type, level_id=level_id)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        if identifier:
            # Try to resolve by UUID or name
            result = handler.get(identifier)
            if not result:
                result = handler.get_by_name(identifier)
            if not result:
                console.print(f"[red]Error:[/red] Policy '{identifier}' not found.")
                raise typer.Exit(1)
            printer.print(result)
        else:
            # List policies
            results = handler.list()
            if name:
                results = [p for p in results if name.lower() in p.get("name", "").lower()]
            printer.print(results, policy_columns())
    finally:
        client.close()


@app.command("bindings")
@app.command("binding")
def get_bindings(
    group_id: Optional[str] = typer.Option(None, "--group", "-g", help="Filter by group UUID"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List IAM policy bindings."""
    from dtiam.resources.bindings import BindingHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = BindingHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        if group_id:
            results = handler.get_for_group(group_id)
        else:
            results = handler.list()
        printer.print(results, binding_columns())
    finally:
        client.close()


@app.command("environments")
@app.command("envs")
@app.command("env")
def get_environments(
    identifier: Optional[str] = typer.Argument(None, help="Environment ID or name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List or get Dynatrace environments (tenants)."""
    from dtiam.resources.environments import EnvironmentHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = EnvironmentHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        if identifier:
            # Try to resolve by ID or name
            result = handler.get(identifier)
            if not result:
                result = handler.get_by_name(identifier)
            if not result:
                console.print(f"[red]Error:[/red] Environment '{identifier}' not found.")
                raise typer.Exit(1)
            printer.print(result)
        else:
            # List environments
            results = handler.list()
            printer.print(results, environment_columns())
    finally:
        client.close()


@app.command("boundaries")
@app.command("boundary")
def get_boundaries(
    identifier: Optional[str] = typer.Argument(None, help="Boundary UUID or name"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List or get IAM policy boundaries."""
    from dtiam.resources.boundaries import BoundaryHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = BoundaryHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        if identifier:
            # Try to resolve by UUID or name
            result = handler.get(identifier)
            if not result:
                result = handler.get_by_name(identifier)
            if not result:
                console.print(f"[red]Error:[/red] Boundary '{identifier}' not found.")
                raise typer.Exit(1)
            printer.print(result)
        else:
            # List boundaries
            results = handler.list()
            if name:
                results = [b for b in results if name.lower() in b.get("name", "").lower()]
            printer.print(results, boundary_columns())
    finally:
        client.close()
