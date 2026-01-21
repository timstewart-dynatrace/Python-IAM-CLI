"""Account-level commands for limits and subscriptions."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

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


# --- Limits Commands ---

@app.command("limits")
def list_limits(
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List account limits and quotas.

    Shows current usage and maximum allowed values for account resources
    like users, groups, environments, etc.

    Example:
        dtiam account limits
        dtiam account limits -o json
    """
    from dtiam.resources.limits import AccountLimitsHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = AccountLimitsHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        summary = handler.get_summary()
        limits = summary.get("limits", [])

        if not limits:
            console.print("No limits found or limits API not available.")
            return

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            printer.print(summary)
        else:
            # Create a nice table
            table = Table(title="Account Limits")
            table.add_column("Limit", style="cyan")
            table.add_column("Current", justify="right")
            table.add_column("Max", justify="right")
            table.add_column("Available", justify="right")
            table.add_column("Usage %", justify="right")
            table.add_column("Status", justify="center")

            for limit in limits:
                status = limit.get("status", "ok")
                if status == "at_capacity":
                    status_style = "[red]AT CAPACITY[/red]"
                elif status == "near_capacity":
                    status_style = "[yellow]NEAR CAPACITY[/yellow]"
                else:
                    status_style = "[green]OK[/green]"

                available = limit.get("available")
                available_str = str(available) if available is not None else "∞"

                max_val = limit.get("max", 0)
                max_str = str(max_val) if max_val else "∞"

                table.add_row(
                    limit.get("name", ""),
                    str(limit.get("current", 0)),
                    max_str,
                    available_str,
                    f"{limit.get('usage_percent', 0)}%",
                    status_style,
                )

            console.print(table)

            # Summary
            if summary.get("limits_at_capacity", 0) > 0:
                console.print(
                    f"\n[red]Warning:[/red] {summary['limits_at_capacity']} limit(s) at capacity"
                )
            if summary.get("limits_near_capacity", 0) > 0:
                console.print(
                    f"[yellow]Note:[/yellow] {summary['limits_near_capacity']} limit(s) near capacity (>80%)"
                )

    finally:
        client.close()


@app.command("check-capacity")
def check_capacity(
    limit: str = typer.Argument(..., help="Limit name to check (e.g., maxUsers, maxGroups)"),
    count: int = typer.Option(1, "--count", "-n", help="Number of resources to add"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Check if there's capacity for additional resources.

    Example:
        dtiam account check-capacity maxUsers
        dtiam account check-capacity maxGroups --count 5
    """
    from dtiam.resources.limits import AccountLimitsHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = AccountLimitsHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        result = handler.check_capacity(limit, count)

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            printer.print(result)
        else:
            if not result.get("found"):
                console.print(f"[yellow]Warning:[/yellow] {result.get('message')}")
                return

            if result.get("has_capacity"):
                console.print(f"[green]✓[/green] {result.get('message')}")
                console.print(f"  Current: {result.get('current')} / {result.get('max')}")
            else:
                console.print(f"[red]✗[/red] {result.get('message')}")
                console.print(f"  Current: {result.get('current')} / {result.get('max')}")
                raise typer.Exit(1)

    finally:
        client.close()


# --- Subscription Commands ---

@app.command("subscriptions")
def list_subscriptions(
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List account subscriptions.

    Shows all subscriptions associated with the account including
    type, status, and time period.

    Example:
        dtiam account subscriptions
        dtiam account subscriptions -o json
    """
    from dtiam.resources.subscriptions import SubscriptionHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = SubscriptionHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        summary = handler.get_summary()
        subscriptions = summary.get("subscriptions", [])

        if not subscriptions:
            console.print("No subscriptions found.")
            return

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            printer.print(summary)
        else:
            console.print(f"Total Subscriptions: {summary.get('total_subscriptions', 0)}")
            console.print(f"Active: {summary.get('active_subscriptions', 0)}\n")

            printer.print(
                subscriptions,
                [
                    ("uuid", "UUID"),
                    ("name", "NAME"),
                    ("type", "TYPE"),
                    ("status", "STATUS"),
                    ("start_time", "START"),
                    ("end_time", "END"),
                ],
            )

    finally:
        client.close()


@app.command("subscription")
def get_subscription(
    subscription: str = typer.Argument(..., help="Subscription UUID or name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Get details of a specific subscription.

    Example:
        dtiam account subscription my-subscription
        dtiam account subscription abc-123-def -o json
    """
    from dtiam.resources.subscriptions import SubscriptionHandler
    from dtiam.commands.describe import print_detail_view

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = SubscriptionHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        # Try by UUID first, then by name
        result = handler.get(subscription)
        if not result:
            result = handler.get_by_name(subscription)

        if not result:
            console.print(f"[red]Error:[/red] Subscription '{subscription}' not found.")
            raise typer.Exit(1)

        if output:
            printer.print(result)
        else:
            print_detail_view(result, f"Subscription: {result.get('name', subscription)}")

    finally:
        client.close()


@app.command("forecast")
def get_forecast(
    subscription: Optional[str] = typer.Argument(None, help="Subscription UUID (optional)"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Get usage forecast for subscriptions.

    Shows predicted usage based on current consumption patterns.

    Example:
        dtiam account forecast
        dtiam account forecast abc-123-def
    """
    from dtiam.resources.subscriptions import SubscriptionHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = SubscriptionHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        result = handler.get_forecast(subscription)

        if not result:
            console.print("No forecast data available.")
            return

        printer.print(result)

    finally:
        client.close()


@app.command("capabilities")
def list_capabilities(
    subscription: Optional[str] = typer.Argument(None, help="Subscription UUID (optional)"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List subscription capabilities.

    Shows what features and capabilities are included in subscriptions.

    Example:
        dtiam account capabilities
        dtiam account capabilities abc-123-def
    """
    from dtiam.resources.subscriptions import SubscriptionHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    handler = SubscriptionHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        capabilities = handler.get_capabilities(subscription)

        if not capabilities:
            console.print("No capabilities found.")
            return

        printer.print(capabilities)

    finally:
        client.close()
