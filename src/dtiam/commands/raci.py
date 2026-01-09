"""RACI matrix generation for IAM governance."""

from __future__ import annotations

import csv
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


# RACI role definitions based on permissions
RACI_DEFINITIONS = {
    "basic": {
        "description": "Basic RACI matrix for common IAM activities",
        "activities": [
            {
                "name": "View Settings",
                "required_permissions": ["settings:objects:read"],
                "raci_role": "I",  # Informed
            },
            {
                "name": "Modify Settings",
                "required_permissions": ["settings:objects:write"],
                "raci_role": "R",  # Responsible
            },
            {
                "name": "Manage Users",
                "required_permissions": ["account:users:write"],
                "raci_role": "A",  # Accountable
            },
            {
                "name": "Manage Groups",
                "required_permissions": ["account:groups:write"],
                "raci_role": "A",
            },
            {
                "name": "Manage Policies",
                "required_permissions": ["account:policies:write"],
                "raci_role": "A",
            },
            {
                "name": "View Users",
                "required_permissions": ["account:users:read"],
                "raci_role": "C",  # Consulted
            },
            {
                "name": "View Groups",
                "required_permissions": ["account:groups:read"],
                "raci_role": "C",
            },
        ],
    },
    "enterprise": {
        "description": "Enterprise RACI matrix with detailed activities",
        "activities": [
            # Configuration Management
            {
                "name": "View Configuration",
                "category": "Configuration",
                "required_permissions": ["settings:objects:read", "settings:schemas:read"],
                "raci_role": "I",
            },
            {
                "name": "Modify Configuration",
                "category": "Configuration",
                "required_permissions": ["settings:objects:write"],
                "raci_role": "R",
            },
            # User Management
            {
                "name": "View Users",
                "category": "User Management",
                "required_permissions": ["account:users:read"],
                "raci_role": "C",
            },
            {
                "name": "Create/Delete Users",
                "category": "User Management",
                "required_permissions": ["account:users:write"],
                "raci_role": "A",
            },
            {
                "name": "Manage User Groups",
                "category": "User Management",
                "required_permissions": ["account:groups:write"],
                "raci_role": "R",
            },
            # Access Control
            {
                "name": "View Policies",
                "category": "Access Control",
                "required_permissions": ["account:policies:read"],
                "raci_role": "C",
            },
            {
                "name": "Create/Modify Policies",
                "category": "Access Control",
                "required_permissions": ["account:policies:write"],
                "raci_role": "A",
            },
            {
                "name": "Manage Role Assignments",
                "category": "Access Control",
                "required_permissions": ["environment:roles:manage"],
                "raci_role": "A",
            },
            # Monitoring
            {
                "name": "View Audit Logs",
                "category": "Monitoring",
                "required_permissions": ["account:audit-log:read"],
                "raci_role": "C",
            },
            {
                "name": "Generate Reports",
                "category": "Monitoring",
                "required_permissions": ["account:users:read", "account:groups:read"],
                "raci_role": "I",
            },
        ],
    },
}


def check_permission_match(group_permissions: set[str], required: list[str]) -> bool:
    """Check if a group has any of the required permissions.

    Args:
        group_permissions: Set of permissions the group has
        required: List of required permissions

    Returns:
        True if any required permission is present
    """
    for req in required:
        # Exact match
        if req in group_permissions:
            return True
        # Wildcard match (e.g., "settings:*" matches "settings:objects:read")
        for perm in group_permissions:
            if "*" in req:
                base = req.replace("*", "")
                if perm.startswith(base):
                    return True
            if "*" in perm:
                base = perm.replace("*", "")
                if req.startswith(base):
                    return True
    return False


@app.command("generate")
def generate_raci(
    template: str = typer.Option("basic", "--template", "-t", help="RACI template (basic, enterprise)"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
    export_file: Optional[Path] = typer.Option(None, "--export", "-e", help="Export to CSV file"),
) -> None:
    """Generate a RACI matrix for IAM governance.

    Creates a matrix showing which groups are Responsible, Accountable,
    Consulted, or Informed for various IAM activities.

    Templates:
    - basic: Simple RACI for common activities
    - enterprise: Detailed RACI with categorized activities
    """
    from dtiam.resources.groups import GroupHandler
    from dtiam.resources.bindings import BindingHandler
    from dtiam.resources.policies import PolicyHandler
    from dtiam.utils.permissions import parse_statement_query

    if template not in RACI_DEFINITIONS:
        console.print(f"[red]Error:[/red] Unknown template: {template}")
        console.print(f"Available templates: {', '.join(RACI_DEFINITIONS.keys())}")
        raise typer.Exit(1)

    raci_template = RACI_DEFINITIONS[template]

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    group_handler = GroupHandler(client)
    binding_handler = BindingHandler(client)
    policy_handler = PolicyHandler(
        client, level_type="account", level_id=client.account_uuid
    )

    try:
        # Get all groups and their permissions
        groups = group_handler.list()
        group_permissions_map = {}

        for group in groups:
            group_uuid = group.get("uuid", "")
            group_name = group.get("name", "")

            # Get bindings and extract permissions
            bindings = binding_handler.get_for_group(group_uuid)
            permissions = set()

            for binding in bindings:
                policy_uuid = binding.get("policyUuid", "")
                policy = policy_handler.get(policy_uuid)

                if policy:
                    statement = policy.get("statementQuery", "")
                    parsed = parse_statement_query(statement)
                    for perm in parsed:
                        if perm["effect"] == "ALLOW":
                            permissions.add(perm["action"])

            group_permissions_map[group_name] = {
                "uuid": group_uuid,
                "permissions": permissions,
            }

        # Build RACI matrix
        matrix = []
        for activity in raci_template["activities"]:
            row = {
                "activity": activity["name"],
                "category": activity.get("category", ""),
                "required_permissions": ", ".join(activity["required_permissions"]),
            }

            for group_name, group_data in group_permissions_map.items():
                if check_permission_match(group_data["permissions"], activity["required_permissions"]):
                    row[group_name] = activity["raci_role"]
                else:
                    row[group_name] = ""

            matrix.append(row)

        result = {
            "template": template,
            "description": raci_template["description"],
            "groups": list(group_permissions_map.keys()),
            "activities": [a["name"] for a in raci_template["activities"]],
            "matrix": matrix,
        }

        # Export to CSV
        if export_file:
            with open(export_file, "w", newline="") as f:
                if matrix:
                    fieldnames = ["activity", "category", "required_permissions"] + list(group_permissions_map.keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(matrix)
            console.print(f"[green]Exported[/green] RACI matrix to {export_file}")
            return

        fmt = output or get_output_format()

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            printer = Printer(format=fmt, plain=is_plain_mode())
            printer.print(result)
            return

        # Table output
        console.print()
        console.print(f"[bold]RACI Matrix ({template})[/bold]")
        console.print(f"[dim]{raci_template['description']}[/dim]")
        console.print()
        console.print("Legend: R=Responsible, A=Accountable, C=Consulted, I=Informed")
        console.print()

        # Create table
        table = Table(show_header=True, header_style="bold")
        table.add_column("Activity")

        # Limit groups for display
        display_groups = list(group_permissions_map.keys())[:8]
        for group in display_groups:
            # Shorten group name
            short_name = group[:12] + "..." if len(group) > 15 else group
            table.add_column(short_name, justify="center")

        if len(group_permissions_map) > 8:
            table.add_column("...", justify="center")

        for row in matrix:
            cells = [row["activity"]]
            for group in display_groups:
                role = row.get(group, "")
                if role == "R":
                    cells.append("[green]R[/green]")
                elif role == "A":
                    cells.append("[red]A[/red]")
                elif role == "C":
                    cells.append("[yellow]C[/yellow]")
                elif role == "I":
                    cells.append("[blue]I[/blue]")
                else:
                    cells.append("")

            if len(group_permissions_map) > 8:
                cells.append("")

            table.add_row(*cells)

        console.print(table)

        if len(group_permissions_map) > 8:
            console.print()
            console.print(f"[dim]Showing {len(display_groups)} of {len(group_permissions_map)} groups. Use --export for full matrix.[/dim]")

    finally:
        client.close()


@app.command("templates")
def list_templates() -> None:
    """List available RACI templates."""
    console.print()
    console.print("[bold]Available RACI Templates[/bold]")
    console.print()

    for name, template in RACI_DEFINITIONS.items():
        console.print(f"[cyan]{name}[/cyan]: {template['description']}")
        console.print(f"  Activities: {len(template['activities'])}")
        console.print()
