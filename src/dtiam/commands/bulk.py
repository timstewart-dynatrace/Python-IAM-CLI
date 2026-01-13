"""Bulk operations for IAM resources."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
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


def load_input_file(file_path: Path) -> list[dict]:
    """Load data from a file (JSON, YAML, or CSV).

    Args:
        file_path: Path to the input file

    Returns:
        List of dictionaries with the data
    """
    suffix = file_path.suffix.lower()
    content = file_path.read_text()

    if suffix == ".json":
        data = json.loads(content)
        return data if isinstance(data, list) else [data]
    elif suffix in (".yaml", ".yml"):
        data = yaml.safe_load(content)
        return data if isinstance(data, list) else [data]
    elif suffix == ".csv":
        reader = csv.DictReader(content.splitlines())
        return list(reader)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use .json, .yaml, .yml, or .csv")


@app.command("add-users-to-group")
def bulk_add_users_to_group(
    file: Path = typer.Option(..., "--file", "-f", help="File with user emails (JSON, YAML, or CSV)"),
    group: str = typer.Option(..., "--group", "-g", help="Group UUID or name"),
    email_field: str = typer.Option("email", "--email-field", "-e", help="Field name containing email addresses"),
    continue_on_error: bool = typer.Option(False, "--continue-on-error", help="Continue processing on errors"),
) -> None:
    """Add multiple users to a group from a file.

    The file can be JSON, YAML, or CSV format.

    JSON/YAML example:
        [{"email": "user1@example.com"}, {"email": "user2@example.com"}]

    CSV example:
        email
        user1@example.com
        user2@example.com
    """
    from dtiam.resources.groups import GroupHandler

    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)

    try:
        records = load_input_file(file)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to read file: {e}")
        raise typer.Exit(1)

    if not records:
        console.print("[yellow]Warning:[/yellow] No records found in file.")
        return

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = GroupHandler(client)

    try:
        # Resolve group
        group_obj = handler.get(group)
        if not group_obj:
            group_obj = handler.get_by_name(group)
        if not group_obj:
            console.print(f"[red]Error:[/red] Group '{group}' not found.")
            raise typer.Exit(1)

        group_id = group_obj.get("uuid")
        group_name = group_obj.get("name", group)

        # Extract emails
        emails = []
        for record in records:
            email = record.get(email_field)
            if email:
                emails.append(email.strip())
            else:
                console.print(f"[yellow]Warning:[/yellow] Record missing '{email_field}' field: {record}")

        if not emails:
            console.print("[red]Error:[/red] No valid email addresses found.")
            raise typer.Exit(1)

        console.print(f"Found {len(emails)} users to add to group '{group_name}'")

        if is_dry_run():
            console.print("[yellow]Dry-run mode:[/yellow] Would add the following users:")
            for email in emails:
                console.print(f"  - {email}")
            return

        # Process additions
        results = {"success": [], "failed": []}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Adding users...", total=len(emails))

            for email in emails:
                try:
                    success = handler.add_member(group_id, email)
                    if success:
                        results["success"].append(email)
                    else:
                        results["failed"].append({"email": email, "error": "API returned failure"})
                except Exception as e:
                    results["failed"].append({"email": email, "error": str(e)})
                    if not continue_on_error:
                        console.print(f"[red]Error:[/red] Failed to add '{email}': {e}")
                        raise typer.Exit(1)

                progress.advance(task)

        # Print summary
        console.print()
        console.print(f"[green]Successfully added:[/green] {len(results['success'])} users")
        if results["failed"]:
            console.print(f"[red]Failed:[/red] {len(results['failed'])} users")
            for failure in results["failed"]:
                console.print(f"  - {failure['email']}: {failure['error']}")

    finally:
        client.close()


@app.command("remove-users-from-group")
def bulk_remove_users_from_group(
    file: Path = typer.Option(..., "--file", "-f", help="File with user emails/UIDs (JSON, YAML, or CSV)"),
    group: str = typer.Option(..., "--group", "-g", help="Group UUID or name"),
    user_field: str = typer.Option("email", "--user-field", "-u", help="Field name containing email or UID"),
    continue_on_error: bool = typer.Option(False, "--continue-on-error", help="Continue processing on errors"),
    force: bool = typer.Option(False, "--force", "-F", help="Skip confirmation"),
) -> None:
    """Remove multiple users from a group from a file.

    The file can be JSON, YAML, or CSV format containing email addresses or user UIDs.
    """
    from dtiam.resources.groups import GroupHandler
    from dtiam.resources.users import UserHandler

    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)

    try:
        records = load_input_file(file)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to read file: {e}")
        raise typer.Exit(1)

    if not records:
        console.print("[yellow]Warning:[/yellow] No records found in file.")
        return

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    group_handler = GroupHandler(client)
    user_handler = UserHandler(client)

    try:
        # Resolve group
        group_obj = group_handler.get(group)
        if not group_obj:
            group_obj = group_handler.get_by_name(group)
        if not group_obj:
            console.print(f"[red]Error:[/red] Group '{group}' not found.")
            raise typer.Exit(1)

        group_id = group_obj.get("uuid")
        group_name = group_obj.get("name", group)

        # Extract user identifiers and resolve to UIDs
        users_to_remove = []
        for record in records:
            user_id = record.get(user_field)
            if not user_id:
                console.print(f"[yellow]Warning:[/yellow] Record missing '{user_field}' field: {record}")
                continue

            user_id = user_id.strip()
            # If it looks like email, resolve to UID
            if "@" in user_id:
                user_obj = user_handler.get_by_email(user_id)
                if user_obj:
                    users_to_remove.append({"uid": user_obj.get("uid"), "display": user_id})
                else:
                    console.print(f"[yellow]Warning:[/yellow] User not found: {user_id}")
            else:
                users_to_remove.append({"uid": user_id, "display": user_id})

        if not users_to_remove:
            console.print("[red]Error:[/red] No valid users found.")
            raise typer.Exit(1)

        console.print(f"Found {len(users_to_remove)} users to remove from group '{group_name}'")

        if is_dry_run():
            console.print("[yellow]Dry-run mode:[/yellow] Would remove the following users:")
            for user in users_to_remove:
                console.print(f"  - {user['display']}")
            return

        if not force:
            confirm = typer.confirm(f"Remove {len(users_to_remove)} users from group '{group_name}'?")
            if not confirm:
                console.print("Aborted.")
                raise typer.Exit(0)

        # Process removals
        results = {"success": [], "failed": []}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Removing users...", total=len(users_to_remove))

            for user in users_to_remove:
                try:
                    success = group_handler.remove_member(group_id, user["uid"])
                    if success:
                        results["success"].append(user["display"])
                    else:
                        results["failed"].append({"user": user["display"], "error": "API returned failure"})
                except Exception as e:
                    results["failed"].append({"user": user["display"], "error": str(e)})
                    if not continue_on_error:
                        console.print(f"[red]Error:[/red] Failed to remove '{user['display']}': {e}")
                        raise typer.Exit(1)

                progress.advance(task)

        # Print summary
        console.print()
        console.print(f"[green]Successfully removed:[/green] {len(results['success'])} users")
        if results["failed"]:
            console.print(f"[red]Failed:[/red] {len(results['failed'])} users")
            for failure in results["failed"]:
                console.print(f"  - {failure['user']}: {failure['error']}")

    finally:
        client.close()


@app.command("create-groups")
def bulk_create_groups(
    file: Path = typer.Option(..., "--file", "-f", help="File with group definitions (JSON or YAML)"),
    continue_on_error: bool = typer.Option(False, "--continue-on-error", help="Continue processing on errors"),
) -> None:
    """Create multiple groups from a file.

    JSON/YAML example:
        - name: "Group A"
          description: "Description for Group A"
        - name: "Group B"
          description: "Description for Group B"
    """
    from dtiam.resources.groups import GroupHandler

    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)

    try:
        records = load_input_file(file)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to read file: {e}")
        raise typer.Exit(1)

    if not records:
        console.print("[yellow]Warning:[/yellow] No records found in file.")
        return

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = GroupHandler(client)

    try:
        # Validate records have name
        valid_groups = []
        for record in records:
            if "name" not in record:
                console.print(f"[yellow]Warning:[/yellow] Record missing 'name' field: {record}")
                continue
            valid_groups.append(record)

        if not valid_groups:
            console.print("[red]Error:[/red] No valid group definitions found.")
            raise typer.Exit(1)

        console.print(f"Found {len(valid_groups)} groups to create")

        if is_dry_run():
            console.print("[yellow]Dry-run mode:[/yellow] Would create the following groups:")
            for group in valid_groups:
                console.print(f"  - {group['name']}")
            return

        # Process creations
        results = {"success": [], "failed": []}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Creating groups...", total=len(valid_groups))

            for group_def in valid_groups:
                try:
                    result = handler.create(group_def)
                    results["success"].append(result.get("name", group_def["name"]))
                except Exception as e:
                    results["failed"].append({"name": group_def["name"], "error": str(e)})
                    if not continue_on_error:
                        console.print(f"[red]Error:[/red] Failed to create '{group_def['name']}': {e}")
                        raise typer.Exit(1)

                progress.advance(task)

        # Print summary
        console.print()
        console.print(f"[green]Successfully created:[/green] {len(results['success'])} groups")
        if results["failed"]:
            console.print(f"[red]Failed:[/red] {len(results['failed'])} groups")
            for failure in results["failed"]:
                console.print(f"  - {failure['name']}: {failure['error']}")

    finally:
        client.close()


@app.command("create-groups-with-policies")
def bulk_create_groups_with_policies(
    file: Path = typer.Option(..., "--file", "-f", help="CSV file with group, policy, and binding definitions"),
    continue_on_error: bool = typer.Option(False, "--continue-on-error", help="Continue processing on errors"),
) -> None:
    """Bulk create groups with policy bindings, optionally scoped to management zones.

    Creates groups, policy bindings, and management zone boundaries in one operation.
    Boundaries created by this command restrict access to specified management zones
    using Dynatrace's boundary query format. This command does NOT support other
    boundary types (custom queries, security contexts, etc.).

    CSV columns:
      - group_name (required): Name of the group to create
      - policy_name (required): Policy to bind to the group
      - level (optional): 'account' or 'environment' (default: account)
      - level_id (optional): Environment ID if level=environment
      - management_zones (optional): Management zone name(s) to restrict access to
        (pipe-separated for multiple zones, e.g., "Zone1|Zone2")
      - boundary_name (optional): Custom boundary name (default: {group}-Boundary)
      - description (optional): Group description

    Notes:
      - Groups are created if they don't exist
      - Boundaries are only created when management_zones is specified
      - Boundary queries use the format: environment:management-zone IN ("zone")
      - Existing groups/boundaries are reused (idempotent operation)

    Example CSV:
        group_name,policy_name,level,level_id,management_zones,boundary_name,description
        LOB5-TEST,Standard User,account,,,,LOB5 global read access
        LOB5-TEST,Pro User,environment,yhu28601,LOB5,LOB5-Boundary,LOB5 zone-restricted write

    Example:
        dtiam bulk create-groups-with-policies --file examples/bulk/sample_bulk_groups.csv
    """
    from dtiam.resources.bindings import BindingHandler
    from dtiam.resources.boundaries import BoundaryHandler
    from dtiam.resources.groups import GroupHandler
    from dtiam.resources.policies import PolicyHandler

    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)

    # Load CSV file
    try:
        with file.open() as f:
            reader = csv.DictReader(f)
            records = list(reader)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to read CSV file: {e}")
        raise typer.Exit(1)

    if not records:
        console.print("[yellow]Warning:[/yellow] No records found in CSV file.")
        return

    # Validate required columns
    required_cols = ['group_name', 'policy_name']
    if not all(col in records[0] for col in required_cols):
        console.print(f"[red]Error:[/red] CSV must have columns: {', '.join(required_cols)}")
        raise typer.Exit(1)

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    group_handler = GroupHandler(client)
    policy_handler = PolicyHandler(client)
    binding_handler = BindingHandler(client)
    boundary_handler = BoundaryHandler(client)

    try:
        console.print(f"Processing {len(records)} row(s) from {file.name}...\n")

        results = {"success": [], "failed": []}
        groups_created = set()
        boundaries_created = {}

        for i, row in enumerate(records, 1):
            group_name = row.get('group_name', '').strip()
            policy_name = row.get('policy_name', '').strip()
            level = row.get('level', 'account').strip() or 'account'
            level_id = row.get('level_id', '').strip() or None
            zones_str = row.get('management_zones', '').strip()
            boundary_name = row.get('boundary_name', '').strip() or None
            description = row.get('description', '').strip() or None

            # Parse pipe-separated zones
            management_zones = [z.strip() for z in zones_str.split('|') if z.strip()] if zones_str else None

            if not group_name or not policy_name:
                console.print(f"[{i}/{len(records)}] [yellow]Skipped:[/yellow] Missing group_name or policy_name")
                results["failed"].append({"row": i, "error": "Missing required fields"})
                continue

            try:
                # Step 1: Create group if it doesn't exist
                if group_name not in groups_created:
                    existing_group = group_handler.get_by_name(group_name)
                    if not existing_group:
                        if is_dry_run():
                            console.print(f"[{i}/{len(records)}] [yellow]Would create group:[/yellow] {group_name}")
                        else:
                            group_data = {"name": group_name}
                            if description:
                                group_data["description"] = description
                            group_handler.create(group_data)
                            console.print(f"[{i}/{len(records)}] [green]Created group:[/green] {group_name}")
                    groups_created.add(group_name)

                # Step 2: Create boundary if needed
                boundary_uuid = None
                if management_zones:
                    boundary_key = f"{group_name}:{','.join(sorted(management_zones))}"
                    if boundary_key not in boundaries_created:
                        bound_name = boundary_name or f"{group_name}-Boundary"
                        existing_boundary = boundary_handler.get_by_name(bound_name)
                        if existing_boundary:
                            boundary_uuid = existing_boundary.get('uuid')
                        elif is_dry_run():
                            console.print(f"[{i}/{len(records)}] [yellow]Would create boundary:[/yellow] {bound_name}")
                        else:
                            boundary = boundary_handler.create(
                                name=bound_name,
                                management_zones=management_zones
                            )
                            boundary_uuid = boundary.get('uuid')
                            console.print(f"[{i}/{len(records)}] [green]Created boundary:[/green] {bound_name}")
                        boundaries_created[boundary_key] = boundary_uuid
                    else:
                        boundary_uuid = boundaries_created[boundary_key]

                # Step 3: Resolve group and policy UUIDs
                group = group_handler.get_by_name(group_name)
                if not group:
                    raise ValueError(f"Group '{group_name}' not found")
                group_uuid = group.get('uuid')

                policy = policy_handler.get_by_name_all_levels(policy_name)
                if not policy:
                    raise ValueError(f"Policy '{policy_name}' not found")
                policy_uuid = policy.get('uuid')

                # Step 4: Create binding
                binding_data = {
                    "policyUuid": policy_uuid,
                    "groups": [group_uuid]
                }
                if boundary_uuid:
                    binding_data["boundaries"] = [boundary_uuid]

                level_desc = f"{level}" + (f":{level_id}" if level_id else "")
                if is_dry_run():
                    console.print(f"[{i}/{len(records)}] [yellow]Would bind:[/yellow] {policy_name} to {group_name} at {level_desc}")
                else:
                    # Create binding handler for the specific level
                    level_binding_handler = BindingHandler(
                        client,
                        level_type=level,
                        level_id=level_id if level == 'environment' else client.account_uuid
                    )
                    _, action = level_binding_handler.create_or_update(
                        group_uuid=group_uuid,
                        policy_uuid=policy_uuid,
                        boundaries=[boundary_uuid] if boundary_uuid else None
                    )
                    if action == "created":
                        console.print(f"[{i}/{len(records)}] [green]Bound:[/green] {policy_name} to {group_name} at {level_desc}")
                    elif action == "updated":
                        console.print(f"[{i}/{len(records)}] [blue]Updated:[/blue] {policy_name} to {group_name} at {level_desc}")
                    else:
                        console.print(f"[{i}/{len(records)}] [cyan]Unchanged:[/cyan] {policy_name} to {group_name} at {level_desc}")

                results["success"].append({"row": i, "group": group_name, "policy": policy_name})

            except Exception as e:
                error_msg = str(e)
                console.print(f"[{i}/{len(records)}] [red]Error:[/red] {error_msg}")
                results["failed"].append({"row": i, "group": group_name, "error": error_msg})
                if not continue_on_error:
                    raise typer.Exit(1)

        # Print summary
        console.print()
        console.print("=" * 60)
        if is_dry_run():
            console.print("[yellow]DRY RUN SUMMARY:[/yellow]")
        else:
            console.print("[green]SUMMARY:[/green]")
        console.print(f"  Success: {len(results['success'])}")
        console.print(f"  Failed: {len(results['failed'])}")
        console.print(f"  Total: {len(records)}")
        if is_dry_run():
            console.print("\nRun without --dry-run to execute these changes")
        console.print("=" * 60)

        if results["failed"]:
            console.print("\n[red]Failed rows:[/red]")
            for failure in results["failed"]:
                console.print(f"  Row {failure['row']}: {failure['error']}")

    finally:
        client.close()


@app.command("create-bindings")
def bulk_create_bindings(
    file: Path = typer.Option(..., "--file", "-f", help="File with binding definitions (JSON or YAML)"),
    continue_on_error: bool = typer.Option(False, "--continue-on-error", help="Continue processing on errors"),
) -> None:
    """Create multiple policy bindings from a file.

    JSON/YAML example:
        - group: "group-uuid-or-name"
          policy: "policy-uuid-or-name"
          boundary: "optional-boundary-uuid"  # optional
        - group: "another-group"
          policy: "another-policy"
    """
    from dtiam.resources.bindings import BindingHandler
    from dtiam.resources.groups import GroupHandler
    from dtiam.resources.policies import PolicyHandler

    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)

    try:
        records = load_input_file(file)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to read file: {e}")
        raise typer.Exit(1)

    if not records:
        console.print("[yellow]Warning:[/yellow] No records found in file.")
        return

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    binding_handler = BindingHandler(client)
    group_handler = GroupHandler(client)
    policy_handler = PolicyHandler(client, level_type="account", level_id=client.account_uuid)

    try:
        # Validate records
        valid_bindings = []
        for record in records:
            if "group" not in record or "policy" not in record:
                console.print(f"[yellow]Warning:[/yellow] Record missing 'group' or 'policy' field: {record}")
                continue
            valid_bindings.append(record)

        if not valid_bindings:
            console.print("[red]Error:[/red] No valid binding definitions found.")
            raise typer.Exit(1)

        console.print(f"Found {len(valid_bindings)} bindings to create")

        if is_dry_run():
            console.print("[yellow]Dry-run mode:[/yellow] Would create the following bindings:")
            for binding in valid_bindings:
                console.print(f"  - Group: {binding['group']} -> Policy: {binding['policy']}")
            return

        # Process creations
        results = {"success": [], "failed": []}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Creating bindings...", total=len(valid_bindings))

            for binding_def in valid_bindings:
                try:
                    # Resolve group
                    group = group_handler.get(binding_def["group"])
                    if not group:
                        group = group_handler.get_by_name(binding_def["group"])
                    if not group:
                        raise ValueError(f"Group not found: {binding_def['group']}")
                    group_uuid = group.get("uuid")

                    # Resolve policy
                    policy = policy_handler.get(binding_def["policy"])
                    if not policy:
                        policy = policy_handler.get_by_name(binding_def["policy"])
                    if not policy:
                        raise ValueError(f"Policy not found: {binding_def['policy']}")
                    policy_uuid = policy.get("uuid")

                    # Optional boundary
                    boundaries = []
                    if "boundary" in binding_def and binding_def["boundary"]:
                        boundaries = [binding_def["boundary"]]

                    result = binding_handler.create(
                        group_uuid=group_uuid,
                        policy_uuid=policy_uuid,
                        boundaries=boundaries,
                    )
                    results["success"].append(f"{binding_def['group']} -> {binding_def['policy']}")
                except Exception as e:
                    results["failed"].append({
                        "binding": f"{binding_def['group']} -> {binding_def['policy']}",
                        "error": str(e),
                    })
                    if not continue_on_error:
                        console.print(f"[red]Error:[/red] Failed to create binding: {e}")
                        raise typer.Exit(1)

                progress.advance(task)

        # Print summary
        console.print()
        console.print(f"[green]Successfully created:[/green] {len(results['success'])} bindings")
        if results["failed"]:
            console.print(f"[red]Failed:[/red] {len(results['failed'])} bindings")
            for failure in results["failed"]:
                console.print(f"  - {failure['binding']}: {failure['error']}")

    finally:
        client.close()


@app.command("export-group-members")
def export_group_members(
    group: str = typer.Option(..., "--group", "-g", help="Group UUID or name"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("csv", "--format", "-f", help="Output format (csv, json, yaml)"),
) -> None:
    """Export group members to a file.

    Useful for backups or migration purposes.
    """
    from dtiam.resources.groups import GroupHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = GroupHandler(client)

    try:
        # Resolve group
        group_obj = handler.get(group)
        if not group_obj:
            group_obj = handler.get_by_name(group)
        if not group_obj:
            console.print(f"[red]Error:[/red] Group '{group}' not found.")
            raise typer.Exit(1)

        group_id = group_obj.get("uuid")
        group_name = group_obj.get("name", group)

        # Get members
        members = handler.get_members(group_id)

        if not members:
            console.print(f"Group '{group_name}' has no members.")
            return

        # Format output
        if format == "json":
            output = json.dumps(members, indent=2)
        elif format == "yaml":
            output = yaml.dump(members, default_flow_style=False)
        elif format == "csv":
            if members:
                fields = list(members[0].keys())
                lines = [",".join(fields)]
                for member in members:
                    row = [str(member.get(f, "")) for f in fields]
                    lines.append(",".join(row))
                output = "\n".join(lines)
        else:
            console.print(f"[red]Error:[/red] Unknown format: {format}")
            raise typer.Exit(1)

        # Write or print output
        if output_file:
            output_file.write_text(output)
            console.print(f"[green]Exported[/green] {len(members)} members to {output_file}")
        else:
            console.print(output)

    finally:
        client.close()
