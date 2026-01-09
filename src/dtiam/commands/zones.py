"""Zone management commands for Dynatrace management zones."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
import yaml
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


def zone_columns() -> list[tuple[str, str]]:
    """Return column definitions for zones."""
    return [
        ("id", "ID"),
        ("name", "Name"),
    ]


@app.command("list")
def list_zones(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List management zones."""
    from dtiam.resources.zones import ZoneHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = ZoneHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        results = handler.list()

        if name:
            results = [z for z in results if name.lower() in z.get("name", "").lower()]

        printer.print(results, zone_columns())

    finally:
        client.close()


@app.command("get")
def get_zone(
    identifier: str = typer.Argument(..., help="Zone ID or name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Get a management zone by ID or name."""
    from dtiam.resources.zones import ZoneHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = ZoneHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        result = handler.get(identifier)
        if not result:
            result = handler.get_by_name(identifier)

        if not result:
            console.print(f"[red]Error:[/red] Zone '{identifier}' not found.")
            raise typer.Exit(1)

        printer.print(result)

    finally:
        client.close()


@app.command("export")
def export_zones(
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("yaml", "--format", "-f", help="Output format (yaml, json, csv)"),
) -> None:
    """Export management zones to a file."""
    from dtiam.resources.zones import ZoneHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = ZoneHandler(client)

    try:
        zones = handler.list()

        if not zones:
            console.print("No zones found.")
            return

        # Format output
        if format == "json":
            output = json.dumps(zones, indent=2)
        elif format == "csv":
            lines = ["id,name"]
            for zone in zones:
                lines.append(f"{zone.get('id', '')},{zone.get('name', '')}")
            output = "\n".join(lines)
        else:  # yaml
            output = yaml.dump(zones, default_flow_style=False)

        if output_file:
            output_file.write_text(output)
            console.print(f"[green]Exported[/green] {len(zones)} zones to {output_file}")
        else:
            console.print(output)

    finally:
        client.close()


@app.command("compare-groups")
def compare_zones_groups(
    case_sensitive: bool = typer.Option(False, "--case-sensitive", "-c", help="Use case-sensitive matching"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Compare zone names with group names to find matches.

    This is useful for identifying zones that have corresponding groups
    and vice versa.
    """
    from dtiam.resources.zones import ZoneHandler
    from dtiam.resources.groups import GroupHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    zone_handler = ZoneHandler(client)
    group_handler = GroupHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        groups = group_handler.list()
        result = zone_handler.compare_with_groups(groups, case_sensitive=case_sensitive)

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            printer.print(result)
            return

        # Table output
        console.print()
        console.print(f"[bold]Zone/Group Comparison[/bold] (case-sensitive: {case_sensitive})")
        console.print()

        # Matched
        console.print(f"[green]Matched:[/green] {result['matched_count']}")
        if result["matched"]:
            match_table = Table(show_header=True, header_style="dim")
            match_table.add_column("Zone Name")
            match_table.add_column("Group Name")
            for match in result["matched"][:20]:
                match_table.add_row(match["zone_name"], match["group_name"])
            if len(result["matched"]) > 20:
                console.print(f"  (showing first 20 of {len(result['matched'])})")
            console.print(match_table)
        console.print()

        # Unmatched zones
        console.print(f"[yellow]Unmatched Zones:[/yellow] {result['unmatched_zones_count']}")
        if result["unmatched_zones"]:
            for zone in result["unmatched_zones"][:10]:
                console.print(f"  - {zone}")
            if len(result["unmatched_zones"]) > 10:
                console.print(f"  ... and {len(result['unmatched_zones']) - 10} more")
        console.print()

        # Unmatched groups
        console.print(f"[yellow]Unmatched Groups:[/yellow] {result['unmatched_groups_count']}")
        if result["unmatched_groups"]:
            for group in result["unmatched_groups"][:10]:
                console.print(f"  - {group}")
            if len(result["unmatched_groups"]) > 10:
                console.print(f"  ... and {len(result['unmatched_groups']) - 10} more")

    finally:
        client.close()
