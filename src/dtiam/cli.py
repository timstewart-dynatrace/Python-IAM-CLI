"""Main CLI entry point for dtiam.

Provides the root command and registers all subcommands.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

import typer
from rich.console import Console

from dtiam import __version__
from dtiam.commands import config as config_cmd
from dtiam.output import OutputFormat

# Create console for rich output
console = Console()

# Create the main Typer app
app = typer.Typer(
    name="dtiam",
    help=(
        "A kubectl-inspired CLI for managing Dynatrace Identity and Access Management.\n\n"
        "[dim]DISCLAIMER: This tool is provided as-is without warranty. Use at your own risk. "
        "NOT produced, endorsed, or supported by Dynatrace.[/dim]"
    ),
    add_completion=True,
    no_args_is_help=True,
    rich_markup_mode="rich",
)


# Global state for shared options
class State:
    """Global state shared across commands."""

    def __init__(self) -> None:
        self.context: str | None = None
        self.output: OutputFormat = OutputFormat.TABLE
        self.verbose: bool = False
        self.plain: bool = False
        self.dry_run: bool = False


state = State()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"dtiam version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    context: Optional[str] = typer.Option(
        None,
        "--context",
        "-c",
        help="Override the current context",
        envvar="DTIAM_CONTEXT",
    ),
    output: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--output",
        "-o",
        help="Output format",
        envvar="DTIAM_OUTPUT",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose/debug output",
        envvar="DTIAM_VERBOSE",
    ),
    plain: bool = typer.Option(
        False,
        "--plain",
        help="Plain output mode (no colors, no prompts)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview changes without applying them",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """dtiam - A kubectl-inspired CLI for managing Dynatrace IAM resources.

    Use 'dtiam <command> --help' for more information about a command.

    Examples:
        dtiam config set-credentials prod --client-id XXX --client-secret YYY
        dtiam config set-context prod --account-uuid UUID --credentials-ref prod
        dtiam config use-context prod
        dtiam get groups
        dtiam get policies
        dtiam describe group "My Group"
    """
    # Store global options in state
    state.context = context
    state.output = output
    state.verbose = verbose
    state.plain = plain
    state.dry_run = dry_run

    # Configure logging
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


# Register subcommands
app.add_typer(config_cmd.app, name="config", help="Manage configuration contexts and credentials")

# Import and register all commands
from dtiam.commands import get as get_cmd
from dtiam.commands import describe as describe_cmd
from dtiam.commands import create as create_cmd
from dtiam.commands import delete as delete_cmd
from dtiam.commands import user as user_cmd
from dtiam.commands import bulk as bulk_cmd
from dtiam.commands import template as template_cmd
from dtiam.commands import zones as zones_cmd
from dtiam.commands import analyze as analyze_cmd
from dtiam.commands import export as export_cmd
from dtiam.commands import group as group_cmd
from dtiam.commands import boundary as boundary_cmd
from dtiam.commands import cache as cache_cmd
from dtiam.commands import service_user as service_user_cmd
from dtiam.commands import account as account_cmd
from dtiam.commands import platform_token as platform_token_cmd

app.add_typer(get_cmd.app, name="get", help="Get/list resources")
app.add_typer(describe_cmd.app, name="describe", help="Show detailed resource information")
app.add_typer(create_cmd.app, name="create", help="Create resources")
app.add_typer(delete_cmd.app, name="delete", help="Delete resources")
app.add_typer(user_cmd.app, name="user", help="User management operations")
app.add_typer(bulk_cmd.app, name="bulk", help="Bulk operations for multiple resources")
app.add_typer(template_cmd.app, name="template", help="Template-based resource creation")
app.add_typer(zones_cmd.app, name="zones", help="Management zone operations [dim](LEGACY - will be removed)[/dim]")
app.add_typer(analyze_cmd.app, name="analyze", help="Analyze permissions and policies")
app.add_typer(export_cmd.app, name="export", help="Export resources and data")
app.add_typer(group_cmd.app, name="group", help="Advanced group operations")
app.add_typer(boundary_cmd.app, name="boundary", help="Boundary attach/detach operations")
app.add_typer(cache_cmd.app, name="cache", help="Cache management")
app.add_typer(service_user_cmd.app, name="service-user", help="Service user (OAuth client) management")
app.add_typer(account_cmd.app, name="account", help="Account limits and subscriptions")
app.add_typer(platform_token_cmd.app, name="platform-token", help="Platform token management")


def main_cli() -> None:
    """Main entry point for the CLI."""
    try:
        app()
    except Exception as e:
        if state.verbose:
            console.print_exception()
        else:
            console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


# Alias for the entry point
def main() -> None:
    """Entry point alias."""
    main_cli()


if __name__ == "__main__":
    main_cli()
