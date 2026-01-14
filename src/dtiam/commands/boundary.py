"""Boundary management commands."""

from __future__ import annotations

import os
from pathlib import Path
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


@app.command("create-app-boundary")
def create_app_boundary(
    name: str = typer.Argument(..., help="Boundary name"),
    app_ids: Optional[list[str]] = typer.Option(
        None, "--app-id", "-a", help="App ID to include (repeatable)"
    ),
    file: Optional[Path] = typer.Option(
        None, "--file", "-f", help="File with app IDs (one per line)"
    ),
    not_in: bool = typer.Option(
        False, "--not-in", help="Use NOT IN instead of IN (exclude apps)"
    ),
    environment: Optional[str] = typer.Option(
        None, "--environment", "-e", help="Environment URL for app validation"
    ),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Boundary description"
    ),
    skip_validation: bool = typer.Option(
        False, "--skip-validation", help="Skip app ID validation against registry"
    ),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Create a boundary restricting access to specific apps.

    Creates a boundary with shared:app-id IN or NOT IN conditions.
    Validates app IDs against the App Engine Registry API before creating.

    Examples:
        # Allow specific apps only
        dtiam boundary create-app-boundary "DashboardAccess" \\
          --app-id "dynatrace.dashboards" \\
          --app-id "dynatrace.notebooks" \\
          -e "abc12345.apps.dynatrace.com"

        # Exclude specific apps (NOT IN)
        dtiam boundary create-app-boundary "NoLegacyApps" \\
          --app-id "dynatrace.classic.smartscape" \\
          --not-in \\
          -e "abc12345.apps.dynatrace.com"

        # Load app IDs from file
        dtiam boundary create-app-boundary "FromFile" \\
          --file app-ids.txt \\
          -e "abc12345.apps.dynatrace.com"
    """
    from dtiam.resources.boundaries import BoundaryHandler
    from dtiam.resources.apps import AppHandler
    from dtiam.output import boundary_columns

    # Collect app IDs from options and file
    all_app_ids: list[str] = []

    if app_ids:
        all_app_ids.extend(app_ids)

    if file:
        if not file.exists():
            console.print(f"[red]Error:[/red] File not found: {file}")
            raise typer.Exit(1)
        with open(file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    all_app_ids.append(line)

    if not all_app_ids:
        console.print("[red]Error:[/red] No app IDs provided. Use --app-id or --file.")
        raise typer.Exit(1)

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique_app_ids: list[str] = []
    for aid in all_app_ids:
        if aid not in seen:
            seen.add(aid)
            unique_app_ids.append(aid)

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    try:
        # Validate app IDs unless skipped
        if not skip_validation:
            env_url = environment or os.environ.get("DTIAM_ENVIRONMENT_URL")
            if not env_url:
                console.print(
                    "[red]Error:[/red] Environment URL required for validation.\n"
                    "Use --environment or set DTIAM_ENVIRONMENT_URL.\n"
                    "Or use --skip-validation to skip app ID validation."
                )
                raise typer.Exit(1)

            app_handler = AppHandler(client, env_url)
            valid_ids, invalid_ids = app_handler.validate_app_ids(unique_app_ids)

            if invalid_ids:
                console.print("[red]Error:[/red] The following app IDs are not valid:")
                for aid in invalid_ids:
                    console.print(f"  - {aid}")
                console.print()

                # Show valid app IDs for reference
                all_valid = app_handler.get_ids()
                if all_valid:
                    console.print("[yellow]Valid app IDs in this environment:[/yellow]")
                    for aid in sorted(all_valid)[:20]:
                        console.print(f"  - {aid}")
                    if len(all_valid) > 20:
                        console.print(f"  ... and {len(all_valid) - 20} more")
                console.print()
                console.print("Use --skip-validation to create the boundary anyway.")
                raise typer.Exit(1)

        # Build the boundary
        boundary_handler = BoundaryHandler(client)
        operator = "NOT IN" if not_in else "IN"

        if is_dry_run():
            query = boundary_handler._build_app_query(unique_app_ids, exclude=not_in)
            console.print(f"[yellow]Dry-run mode:[/yellow] Would create boundary '{name}'")
            console.print(f"  Operator: {operator}")
            console.print(f"  App IDs ({len(unique_app_ids)}):")
            for aid in unique_app_ids:
                console.print(f"    - {aid}")
            console.print(f"\n  Boundary query:\n{query}")
            return

        result = boundary_handler.create_from_apps(
            name=name,
            app_ids=unique_app_ids,
            exclude=not_in,
            description=description,
        )

        if not result:
            console.print("[red]Error:[/red] Failed to create boundary.")
            raise typer.Exit(1)

        from dtiam.cli import state
        fmt = output or state.output
        printer = Printer(format=fmt, plain=state.plain)

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            printer.print(result)
        else:
            console.print(f"[green]Created boundary:[/green] {result.get('name')}")
            console.print(f"  UUID: {result.get('uuid')}")
            console.print(f"  Operator: {operator}")
            console.print(f"  App IDs: {len(unique_app_ids)}")
            if result.get("boundaryQuery"):
                console.print(f"\n  Query:\n{result.get('boundaryQuery')}")

    finally:
        client.close()


@app.command("create-schema-boundary")
def create_schema_boundary(
    name: str = typer.Argument(..., help="Boundary name"),
    schema_ids: Optional[list[str]] = typer.Option(
        None, "--schema-id", "-s", help="Schema ID to include (repeatable)"
    ),
    file: Optional[Path] = typer.Option(
        None, "--file", "-f", help="File with schema IDs (one per line)"
    ),
    not_in: bool = typer.Option(
        False, "--not-in", help="Use NOT IN instead of IN (exclude schemas)"
    ),
    environment: Optional[str] = typer.Option(
        None, "--environment", "-e", help="Environment URL for schema validation"
    ),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Boundary description"
    ),
    skip_validation: bool = typer.Option(
        False, "--skip-validation", help="Skip schema ID validation against environment"
    ),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Create a boundary restricting access to specific settings schemas.

    Creates a boundary with settings:schemaId IN or NOT IN conditions.
    Validates schema IDs against the Settings API before creating.

    Examples:
        # Allow access to specific schemas only
        dtiam boundary create-schema-boundary "AlertingOnly" \\
          --schema-id "builtin:alerting.profile" \\
          --schema-id "builtin:alerting.maintenance-window" \\
          -e "abc12345.live.dynatrace.com"

        # Exclude specific schemas (NOT IN)
        dtiam boundary create-schema-boundary "NoSpanSettings" \\
          --schema-id "builtin:span-attribute" \\
          --schema-id "builtin:span-capture-rule" \\
          --not-in \\
          -e "abc12345.live.dynatrace.com"

        # Load schema IDs from file
        dtiam boundary create-schema-boundary "FromFile" \\
          --file schema-ids.txt \\
          -e "abc12345.live.dynatrace.com"
    """
    from dtiam.resources.boundaries import BoundaryHandler
    from dtiam.resources.schemas import SchemaHandler

    # Collect schema IDs from options and file
    all_schema_ids: list[str] = []

    if schema_ids:
        all_schema_ids.extend(schema_ids)

    if file:
        if not file.exists():
            console.print(f"[red]Error:[/red] File not found: {file}")
            raise typer.Exit(1)
        with open(file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    all_schema_ids.append(line)

    if not all_schema_ids:
        console.print("[red]Error:[/red] No schema IDs provided. Use --schema-id or --file.")
        raise typer.Exit(1)

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique_schema_ids: list[str] = []
    for sid in all_schema_ids:
        if sid not in seen:
            seen.add(sid)
            unique_schema_ids.append(sid)

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    try:
        # Validate schema IDs unless skipped
        if not skip_validation:
            env_url = environment or os.environ.get("DTIAM_ENVIRONMENT_URL")
            if not env_url:
                console.print(
                    "[red]Error:[/red] Environment URL required for validation.\n"
                    "Use --environment or set DTIAM_ENVIRONMENT_URL.\n"
                    "Or use --skip-validation to skip schema ID validation."
                )
                raise typer.Exit(1)

            # Normalize environment URL for Settings API
            if not env_url.startswith("http") and "." not in env_url:
                env_url = f"https://{env_url}.live.dynatrace.com"

            schema_handler = SchemaHandler(client, env_url)
            valid_ids, invalid_ids = schema_handler.validate_schema_ids(unique_schema_ids)

            if invalid_ids:
                console.print("[red]Error:[/red] The following schema IDs are not valid:")
                for sid in invalid_ids:
                    console.print(f"  - {sid}")
                console.print()

                # Show some valid schema IDs for reference
                all_valid = schema_handler.get_builtin_ids()
                if all_valid:
                    console.print("[yellow]Sample valid schema IDs in this environment:[/yellow]")
                    for sid in sorted(all_valid)[:20]:
                        console.print(f"  - {sid}")
                    if len(all_valid) > 20:
                        console.print(f"  ... and {len(all_valid) - 20} more")
                    console.print("\nUse 'dtiam get schemas --search <pattern>' to find schemas.")
                console.print()
                console.print("Use --skip-validation to create the boundary anyway.")
                raise typer.Exit(1)

        # Build the boundary
        boundary_handler = BoundaryHandler(client)
        operator = "NOT IN" if not_in else "IN"

        if is_dry_run():
            query = boundary_handler._build_schema_query(unique_schema_ids, exclude=not_in)
            console.print(f"[yellow]Dry-run mode:[/yellow] Would create boundary '{name}'")
            console.print(f"  Operator: {operator}")
            console.print(f"  Schema IDs ({len(unique_schema_ids)}):")
            for sid in unique_schema_ids:
                console.print(f"    - {sid}")
            console.print(f"\n  Boundary query:\n{query}")
            return

        result = boundary_handler.create_from_schemas(
            name=name,
            schema_ids=unique_schema_ids,
            exclude=not_in,
            description=description,
        )

        if not result:
            console.print("[red]Error:[/red] Failed to create boundary.")
            raise typer.Exit(1)

        from dtiam.cli import state
        fmt = output or state.output
        printer = Printer(format=fmt, plain=state.plain)

        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            printer.print(result)
        else:
            console.print(f"[green]Created boundary:[/green] {result.get('name')}")
            console.print(f"  UUID: {result.get('uuid')}")
            console.print(f"  Operator: {operator}")
            console.print(f"  Schema IDs: {len(unique_schema_ids)}")
            if result.get("boundaryQuery"):
                console.print(f"\n  Query:\n{result.get('boundaryQuery')}")

    finally:
        client.close()
