"""Analysis commands for IAM resources.

Provides effective permissions calculation, permissions matrix generation,
and policy analysis.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from dtiam.client import create_client_from_config
from dtiam.config import load_config
from dtiam.output import OutputFormat, Printer
from dtiam.utils.permissions import (
    PermissionsCalculator,
    PermissionsMatrix,
    EffectivePermissionsAPI,
)

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


@app.command("user-permissions")
def analyze_user_permissions(
    user: str = typer.Argument(..., help="User email or UID"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
    export_file: Optional[Path] = typer.Option(None, "--export", "-e", help="Export to file"),
) -> None:
    """Calculate effective permissions for a user.

    Shows all permissions granted to a user through their group memberships
    and policy bindings.
    """
    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    calculator = PermissionsCalculator(client)

    try:
        result = calculator.get_user_effective_permissions(user)

        if "error" in result:
            console.print(f"[red]Error:[/red] {result['error']}")
            raise typer.Exit(1)

        fmt = output or get_output_format()

        if export_file:
            if export_file.suffix == ".json":
                export_file.write_text(json.dumps(result, indent=2))
            else:
                export_file.write_text(yaml.dump(result, default_flow_style=False))
            console.print(f"[green]Exported[/green] to {export_file}")
            return

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            printer = Printer(format=fmt, plain=is_plain_mode())
            printer.print(result)
            return

        # Formatted output
        console.print()
        console.print(Panel(f"[bold]Effective Permissions: {result['user']['email']}[/bold]"))

        # User info
        console.print(f"UID: {result['user']['uid']}")
        console.print(f"Groups: {result['group_count']}")
        console.print(f"Policy Bindings: {result['binding_count']}")
        console.print(f"Unique Permissions: {result['permission_count']}")
        console.print()

        # Groups
        if result["groups"]:
            console.print("[bold]Group Memberships:[/bold]")
            for group in result["groups"]:
                console.print(f"  - {group['name']}")
            console.print()

        # Permissions table
        if result["effective_permissions"]:
            console.print("[bold]Effective Permissions:[/bold]")
            perm_table = Table(show_header=True)
            perm_table.add_column("Effect", style="green")
            perm_table.add_column("Action")
            perm_table.add_column("Sources")

            for perm in result["effective_permissions"]:
                sources = ", ".join([f"{s['group']}/{s['policy']}" for s in perm["sources"]])
                effect_style = "green" if perm["effect"] == "ALLOW" else "red"
                perm_table.add_row(
                    f"[{effect_style}]{perm['effect']}[/{effect_style}]",
                    perm["action"],
                    sources[:50] + "..." if len(sources) > 50 else sources,
                )

            console.print(perm_table)
        else:
            console.print("[yellow]No permissions found.[/yellow]")

    finally:
        client.close()


@app.command("group-permissions")
def analyze_group_permissions(
    group: str = typer.Argument(..., help="Group UUID or name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
    export_file: Optional[Path] = typer.Option(None, "--export", "-e", help="Export to file"),
) -> None:
    """Calculate effective permissions for a group.

    Shows all permissions granted to a group through its policy bindings.
    """
    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    calculator = PermissionsCalculator(client)

    try:
        result = calculator.get_group_effective_permissions(group)

        if "error" in result:
            console.print(f"[red]Error:[/red] {result['error']}")
            raise typer.Exit(1)

        fmt = output or get_output_format()

        if export_file:
            if export_file.suffix == ".json":
                export_file.write_text(json.dumps(result, indent=2))
            else:
                export_file.write_text(yaml.dump(result, default_flow_style=False))
            console.print(f"[green]Exported[/green] to {export_file}")
            return

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            printer = Printer(format=fmt, plain=is_plain_mode())
            printer.print(result)
            return

        # Formatted output
        console.print()
        console.print(Panel(f"[bold]Effective Permissions: {result['group']['name']}[/bold]"))

        console.print(f"UUID: {result['group']['uuid']}")
        console.print(f"Policy Bindings: {result['binding_count']}")
        console.print(f"Unique Permissions: {result['permission_count']}")
        console.print()

        # Permissions table
        if result["effective_permissions"]:
            console.print("[bold]Effective Permissions:[/bold]")
            perm_table = Table(show_header=True)
            perm_table.add_column("Effect", style="green")
            perm_table.add_column("Action")
            perm_table.add_column("Source Policies")

            for perm in result["effective_permissions"]:
                sources = ", ".join([s["policy"] for s in perm["sources"]])
                effect_style = "green" if perm["effect"] == "ALLOW" else "red"
                perm_table.add_row(
                    f"[{effect_style}]{perm['effect']}[/{effect_style}]",
                    perm["action"],
                    sources[:50] + "..." if len(sources) > 50 else sources,
                )

            console.print(perm_table)
        else:
            console.print("[yellow]No permissions found.[/yellow]")

    finally:
        client.close()


@app.command("permissions-matrix")
def permissions_matrix(
    scope: str = typer.Option("policies", "--scope", "-s", help="Scope: policies or groups"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
    export_file: Optional[Path] = typer.Option(None, "--export", "-e", help="Export to CSV file"),
) -> None:
    """Generate a permissions matrix.

    Shows which permissions are granted by each policy or group.
    Useful for security audits and compliance reviews.
    """
    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    matrix_gen = PermissionsMatrix(client)

    try:
        if scope == "groups":
            result = matrix_gen.generate_group_matrix()
            name_field = "group_name"
        else:
            result = matrix_gen.generate_policy_matrix()
            name_field = "policy_name"

        fmt = output or get_output_format()

        # Export to CSV
        if export_file:
            with open(export_file, "w", newline="") as f:
                if result["matrix"]:
                    writer = csv.DictWriter(f, fieldnames=result["matrix"][0].keys())
                    writer.writeheader()
                    writer.writerows(result["matrix"])
            console.print(f"[green]Exported[/green] matrix to {export_file}")
            return

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            printer = Printer(format=fmt, plain=is_plain_mode())
            printer.print(result)
            return

        # Table output
        console.print()
        console.print(Panel(f"[bold]Permissions Matrix ({scope.title()})[/bold]"))
        console.print(f"Total {scope}: {result.get(f'{scope[:-1]}_count', len(result['matrix']))}")
        console.print(f"Unique permissions: {result['permission_count']}")
        console.print()

        if not result["matrix"]:
            console.print("[yellow]No data found.[/yellow]")
            return

        # Create table with limited columns for readability
        table = Table(show_header=True, header_style="bold")
        table.add_column("Name")

        # Limit to first 5 permissions for table display
        display_perms = result["permissions"][:5]
        for perm in display_perms:
            # Shorten permission name for display
            short_perm = perm.split(":")[-1] if ":" in perm else perm
            table.add_column(short_perm[:15], justify="center")

        if len(result["permissions"]) > 5:
            table.add_column("...", justify="center")

        for row in result["matrix"][:20]:
            cells = [row[name_field]]
            for perm in display_perms:
                cells.append("✓" if row.get(perm) else "")
            if len(result["permissions"]) > 5:
                cells.append("")
            table.add_row(*cells)

        if len(result["matrix"]) > 20:
            console.print(f"(Showing first 20 of {len(result['matrix'])} rows)")

        console.print(table)
        console.print()
        console.print("[dim]Use --export to get full matrix as CSV[/dim]")

    finally:
        client.close()


@app.command("policy")
def analyze_policy(
    identifier: str = typer.Argument(..., help="Policy UUID or name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Analyze a policy's permissions and bindings.

    Shows what permissions a policy grants and where it's bound.
    """
    from dtiam.resources.policies import PolicyHandler
    from dtiam.resources.bindings import BindingHandler
    from dtiam.resources.groups import GroupHandler
    from dtiam.utils.permissions import parse_statement_query

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())

    policy_handler = PolicyHandler(
        client, level_type="account", level_id=client.account_uuid
    )
    binding_handler = BindingHandler(client)
    group_handler = GroupHandler(client)

    try:
        # Get policy
        policy = policy_handler.get(identifier)
        if not policy:
            policy = policy_handler.get_by_name(identifier)

        if not policy:
            console.print(f"[red]Error:[/red] Policy '{identifier}' not found.")
            raise typer.Exit(1)

        policy_uuid = policy.get("uuid", "")
        policy_name = policy.get("name", "")
        statement = policy.get("statementQuery", "")

        # Parse permissions
        permissions = parse_statement_query(statement)

        # Find bindings
        all_bindings = binding_handler.list()
        policy_bindings = [
            b for b in all_bindings
            if b.get("policyUuid") == policy_uuid
        ]

        # Resolve groups
        bound_groups = []
        for binding in policy_bindings:
            group_uuid = binding.get("groupUuid", "")
            group = group_handler.get(group_uuid)
            if group:
                bound_groups.append({
                    "uuid": group_uuid,
                    "name": group.get("name", ""),
                    "boundary": binding.get("boundaryUuid"),
                })

        result = {
            "policy": {
                "uuid": policy_uuid,
                "name": policy_name,
                "description": policy.get("description", ""),
                "statement": statement,
            },
            "permissions": permissions,
            "permission_count": len(permissions),
            "bindings": bound_groups,
            "binding_count": len(bound_groups),
        }

        fmt = output or get_output_format()

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            printer = Printer(format=fmt, plain=is_plain_mode())
            printer.print(result)
            return

        # Formatted output
        console.print()
        console.print(Panel(f"[bold]Policy Analysis: {policy_name}[/bold]"))

        console.print(f"UUID: {policy_uuid}")
        if policy.get("description"):
            console.print(f"Description: {policy.get('description')}")
        console.print()

        # Statement
        console.print("[bold]Statement Query:[/bold]")
        console.print(Panel(statement, expand=False))
        console.print()

        # Permissions
        console.print(f"[bold]Parsed Permissions ({len(permissions)}):[/bold]")
        if permissions:
            perm_table = Table(show_header=True)
            perm_table.add_column("Effect")
            perm_table.add_column("Action")
            perm_table.add_column("Conditions")

            for perm in permissions:
                effect_style = "green" if perm["effect"] == "ALLOW" else "red"
                perm_table.add_row(
                    f"[{effect_style}]{perm['effect']}[/{effect_style}]",
                    perm["action"],
                    perm.get("conditions", "-")[:40] or "-",
                )
            console.print(perm_table)
        else:
            console.print("[yellow]No permissions parsed.[/yellow]")
        console.print()

        # Bindings
        console.print(f"[bold]Bound to Groups ({len(bound_groups)}):[/bold]")
        if bound_groups:
            for group in bound_groups:
                boundary_info = f" (boundary: {group['boundary']})" if group.get("boundary") else ""
                console.print(f"  - {group['name']}{boundary_info}")
        else:
            console.print("[yellow]Not bound to any groups.[/yellow]")

    finally:
        client.close()


@app.command("least-privilege")
def analyze_least_privilege(
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
    export_file: Optional[Path] = typer.Option(None, "--export", "-e", help="Export findings to file"),
) -> None:
    """Analyze policies for least-privilege compliance.

    Identifies policies that may grant excessive permissions.
    """
    from dtiam.resources.policies import PolicyHandler
    from dtiam.utils.permissions import parse_statement_query

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    policy_handler = PolicyHandler(
        client, level_type="account", level_id=client.account_uuid
    )

    # Broad permission patterns that may indicate over-permissioning
    BROAD_PATTERNS = [
        ("*", "Wildcard permission"),
        (":*", "Resource wildcard"),
        ("write", "Write access"),
        ("manage", "Management access"),
        ("delete", "Delete capability"),
        ("admin", "Admin access"),
    ]

    try:
        policies = policy_handler.list()
        findings = []

        for policy in policies:
            policy_uuid = policy.get("uuid", "")
            policy_name = policy.get("name", "")

            policy_detail = policy_handler.get(policy_uuid)
            statement = policy_detail.get("statementQuery", "") if policy_detail else ""

            policy_findings = []

            # Check for broad patterns
            for pattern, description in BROAD_PATTERNS:
                if pattern in statement.lower():
                    policy_findings.append({
                        "type": "broad_permission",
                        "pattern": pattern,
                        "description": description,
                        "severity": "high" if pattern in ["*", "admin"] else "medium",
                    })

            # Check for no conditions (unrestricted)
            permissions = parse_statement_query(statement)
            unrestricted = [p for p in permissions if not p.get("conditions")]
            if unrestricted and len(unrestricted) == len(permissions):
                policy_findings.append({
                    "type": "no_conditions",
                    "description": "All permissions lack conditions/restrictions",
                    "severity": "medium",
                })

            if policy_findings:
                findings.append({
                    "policy_uuid": policy_uuid,
                    "policy_name": policy_name,
                    "findings": policy_findings,
                    "finding_count": len(policy_findings),
                })

        result = {
            "total_policies": len(policies),
            "policies_with_findings": len(findings),
            "findings": findings,
        }

        if export_file:
            if export_file.suffix == ".json":
                export_file.write_text(json.dumps(result, indent=2))
            else:
                export_file.write_text(yaml.dump(result, default_flow_style=False))
            console.print(f"[green]Exported[/green] findings to {export_file}")
            return

        fmt = output or get_output_format()

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            printer = Printer(format=fmt, plain=is_plain_mode())
            printer.print(result)
            return

        # Formatted output
        console.print()
        console.print(Panel("[bold]Least-Privilege Analysis[/bold]"))

        console.print(f"Policies analyzed: {result['total_policies']}")
        console.print(f"Policies with findings: {result['policies_with_findings']}")
        console.print()

        if not findings:
            console.print("[green]No issues found.[/green]")
            return

        for policy_finding in findings:
            console.print(f"[bold]{policy_finding['policy_name']}[/bold]")
            for finding in policy_finding["findings"]:
                severity_color = "red" if finding["severity"] == "high" else "yellow"
                console.print(
                    f"  [{severity_color}]{finding['severity'].upper()}[/{severity_color}]: "
                    f"{finding['description']}"
                )
            console.print()

    finally:
        client.close()


@app.command("effective-user")
def effective_user_permissions(
    user: str = typer.Argument(..., help="User email or UID"),
    level_type: str = typer.Option("account", "--level", "-l", help="Level type: account, environment, global"),
    level_id: str = typer.Option("", "--level-id", help="Level ID (uses account UUID if not specified)"),
    services: str = typer.Option("", "--services", "-s", help="Comma-separated service filter"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
    export_file: Optional[Path] = typer.Option(None, "--export", "-e", help="Export to file"),
) -> None:
    """Get effective permissions for a user via the Dynatrace API.

    This calls the Dynatrace resolution API directly to get permissions as
    computed by the platform, which is the authoritative source.

    Example:
        dtiam analyze effective-user admin@example.com
        dtiam analyze effective-user admin@example.com --level environment --level-id env123
        dtiam analyze effective-user admin@example.com --services settings,entities
    """
    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    api = EffectivePermissionsAPI(client)

    try:
        service_list = [s.strip() for s in services.split(",") if s.strip()] if services else None

        result = api.get_user_effective_permissions(
            user_id=user,
            level_type=level_type,
            level_id=level_id if level_id else None,
            services=service_list,
        )

        if "error" in result:
            console.print(f"[red]Error:[/red] {result['error']}")
            raise typer.Exit(1)

        fmt = output or get_output_format()

        if export_file:
            if export_file.suffix == ".json":
                export_file.write_text(json.dumps(result, indent=2))
            else:
                export_file.write_text(yaml.dump(result, default_flow_style=False))
            console.print(f"[green]Exported[/green] to {export_file}")
            return

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            printer = Printer(format=fmt, plain=is_plain_mode())
            printer.print(result)
            return

        # Formatted output
        console.print()
        console.print(Panel(f"[bold]Effective Permissions (API): {user}[/bold]"))

        console.print(f"Entity ID: {result.get('entityId', user)}")
        console.print(f"Level: {result.get('levelType', level_type)}/{result.get('levelId', 'N/A')}")
        console.print(f"Total Permissions: {result.get('total', 0)}")
        console.print()

        permissions = result.get("effectivePermissions", [])
        if not permissions:
            console.print("[yellow]No effective permissions found.[/yellow]")
            return

        # Display permissions in a table
        table = Table(show_header=True)
        table.add_column("Permission")
        table.add_column("Effect")
        table.add_column("Service")

        for perm in permissions[:50]:  # Limit display
            perm_name = perm.get("permission", perm.get("name", str(perm)))
            effect = perm.get("effect", "ALLOW")
            service = perm.get("service", "-")

            effect_style = "green" if effect.upper() == "ALLOW" else "red"
            table.add_row(
                perm_name,
                f"[{effect_style}]{effect}[/{effect_style}]",
                service,
            )

        console.print(table)

        if len(permissions) > 50:
            console.print(f"\n[dim]Showing 50 of {len(permissions)} permissions. Use --export for full list.[/dim]")

    finally:
        client.close()


@app.command("effective-group")
def effective_group_permissions(
    group: str = typer.Argument(..., help="Group UUID or name"),
    level_type: str = typer.Option("account", "--level", "-l", help="Level type: account, environment, global"),
    level_id: str = typer.Option("", "--level-id", help="Level ID (uses account UUID if not specified)"),
    services: str = typer.Option("", "--services", "-s", help="Comma-separated service filter"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
    export_file: Optional[Path] = typer.Option(None, "--export", "-e", help="Export to file"),
) -> None:
    """Get effective permissions for a group via the Dynatrace API.

    This calls the Dynatrace resolution API directly to get permissions as
    computed by the platform, which is the authoritative source.

    Example:
        dtiam analyze effective-group "DevOps Team"
        dtiam analyze effective-group "DevOps Team" --level environment --level-id env123
    """
    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose(), get_api_url())
    api = EffectivePermissionsAPI(client)

    try:
        service_list = [s.strip() for s in services.split(",") if s.strip()] if services else None

        result = api.get_group_effective_permissions(
            group_id=group,
            level_type=level_type,
            level_id=level_id if level_id else None,
            services=service_list,
        )

        if "error" in result:
            console.print(f"[red]Error:[/red] {result['error']}")
            raise typer.Exit(1)

        fmt = output or get_output_format()

        if export_file:
            if export_file.suffix == ".json":
                export_file.write_text(json.dumps(result, indent=2))
            else:
                export_file.write_text(yaml.dump(result, default_flow_style=False))
            console.print(f"[green]Exported[/green] to {export_file}")
            return

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            printer = Printer(format=fmt, plain=is_plain_mode())
            printer.print(result)
            return

        # Formatted output
        console.print()
        console.print(Panel(f"[bold]Effective Permissions (API): {group}[/bold]"))

        console.print(f"Entity ID: {result.get('entityId', group)}")
        console.print(f"Level: {result.get('levelType', level_type)}/{result.get('levelId', 'N/A')}")
        console.print(f"Total Permissions: {result.get('total', 0)}")
        console.print()

        permissions = result.get("effectivePermissions", [])
        if not permissions:
            console.print("[yellow]No effective permissions found.[/yellow]")
            return

        # Display permissions in a table
        table = Table(show_header=True)
        table.add_column("Permission")
        table.add_column("Effect")
        table.add_column("Service")

        for perm in permissions[:50]:  # Limit display
            perm_name = perm.get("permission", perm.get("name", str(perm)))
            effect = perm.get("effect", "ALLOW")
            service = perm.get("service", "-")

            effect_style = "green" if effect.upper() == "ALLOW" else "red"
            table.add_row(
                perm_name,
                f"[{effect_style}]{effect}[/{effect_style}]",
                service,
            )

        console.print(table)

        if len(permissions) > 50:
            console.print(f"\n[dim]Showing 50 of {len(permissions)} permissions. Use --export for full list.[/dim]")

    finally:
        client.close()

