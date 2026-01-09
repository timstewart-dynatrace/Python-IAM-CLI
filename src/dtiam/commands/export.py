"""Comprehensive export commands for IAM resources."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from dtiam.client import create_client_from_config
from dtiam.config import load_config
from dtiam.output import OutputFormat

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


def write_data(data: list[dict], path: Path, format: str) -> None:
    """Write data to file in specified format.

    Args:
        data: List of dictionaries to write
        path: Output file path
        format: Output format (csv, json, yaml)
    """
    if format == "json":
        path.write_text(json.dumps(data, indent=2, default=str))
    elif format == "yaml":
        path.write_text(yaml.dump(data, default_flow_style=False))
    elif format == "csv":
        if data:
            with open(path, "w", newline="") as f:
                # Flatten nested dicts for CSV
                flat_data = []
                for item in data:
                    flat_item = {}
                    for k, v in item.items():
                        if isinstance(v, (list, dict)):
                            flat_item[k] = json.dumps(v)
                        else:
                            flat_item[k] = v
                    flat_data.append(flat_item)

                writer = csv.DictWriter(f, fieldnames=flat_data[0].keys())
                writer.writeheader()
                writer.writerows(flat_data)
        else:
            path.write_text("")


@app.command("all")
def export_all(
    output_dir: Path = typer.Option(".", "--output", "-o", help="Output directory"),
    format: str = typer.Option("csv", "--format", "-f", help="Output format (csv, json, yaml)"),
    prefix: str = typer.Option("dtiam", "--prefix", "-p", help="File name prefix"),
    include: Optional[str] = typer.Option(
        None, "--include", "-i",
        help="Comma-separated list of exports to include (environments,groups,users,policies,bindings,boundaries)"
    ),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Include detailed/enriched data"),
    timestamp_dir: bool = typer.Option(True, "--timestamp-dir/--no-timestamp-dir", help="Create timestamped subdirectory"),
) -> None:
    """Export all IAM resources to files.

    Exports environments, groups, users, policies, bindings, and boundaries.
    With --detailed flag, includes enriched data like user counts and memberships.

    Examples:
        dtiam export all                          # Export all to CSV in current dir
        dtiam export all -o ./backup -f json      # Export as JSON to backup dir
        dtiam export all --detailed               # Include enriched data
        dtiam export all -i groups,policies       # Only export groups and policies
    """
    from dtiam.resources.environments import EnvironmentHandler
    from dtiam.resources.groups import GroupHandler
    from dtiam.resources.users import UserHandler
    from dtiam.resources.policies import PolicyHandler
    from dtiam.resources.bindings import BindingHandler
    from dtiam.resources.boundaries import BoundaryHandler

    # Determine which exports to run
    all_exports = ["environments", "groups", "users", "policies", "bindings", "boundaries"]
    if include:
        exports_to_run = [e.strip() for e in include.split(",") if e.strip() in all_exports]
    else:
        exports_to_run = all_exports

    if not exports_to_run:
        console.print("[red]Error:[/red] No valid exports specified.")
        raise typer.Exit(1)

    # Create output directory
    if timestamp_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = output_dir / f"{prefix}_export_{timestamp}"
    else:
        export_dir = output_dir

    export_dir.mkdir(parents=True, exist_ok=True)

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    # File extension
    ext = format if format in ["json", "yaml"] else "csv"

    exported_files = []

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # Environments
            if "environments" in exports_to_run:
                task = progress.add_task("Exporting environments...", total=1)
                handler = EnvironmentHandler(client)
                data = handler.list()
                file_path = export_dir / f"{prefix}_environments.{ext}"
                write_data(data, file_path, format)
                exported_files.append(("environments", len(data), file_path))
                progress.advance(task)

            # Groups
            if "groups" in exports_to_run:
                task = progress.add_task("Exporting groups...", total=1)
                handler = GroupHandler(client)
                data = handler.list()

                if detailed:
                    # Enrich with member counts
                    for group in data:
                        group_id = group.get("uuid", "")
                        members = handler.get_members(group_id)
                        group["member_count"] = len(members)
                        group["member_emails"] = [m.get("email", "") for m in members]

                file_path = export_dir / f"{prefix}_groups.{ext}"
                write_data(data, file_path, format)
                exported_files.append(("groups", len(data), file_path))
                progress.advance(task)

            # Users
            if "users" in exports_to_run:
                task = progress.add_task("Exporting users...", total=1)
                handler = UserHandler(client)
                data = handler.list()

                if detailed:
                    # Enrich with group memberships
                    for user in data:
                        user_id = user.get("uid", "")
                        groups = handler.get_groups(user_id)
                        user["group_count"] = len(groups)
                        user["group_names"] = [g.get("name", "") for g in groups]

                file_path = export_dir / f"{prefix}_users.{ext}"
                write_data(data, file_path, format)
                exported_files.append(("users", len(data), file_path))
                progress.advance(task)

            # Policies
            if "policies" in exports_to_run:
                task = progress.add_task("Exporting policies...", total=1)
                handler = PolicyHandler(client, level_type="account", level_id=client.account_uuid)
                data = handler.list()

                if detailed:
                    # Get full policy details
                    detailed_data = []
                    for policy in data:
                        policy_id = policy.get("uuid", "")
                        detail = handler.get(policy_id)
                        if detail:
                            detailed_data.append(detail)
                        else:
                            detailed_data.append(policy)
                    data = detailed_data

                file_path = export_dir / f"{prefix}_policies.{ext}"
                write_data(data, file_path, format)
                exported_files.append(("policies", len(data), file_path))
                progress.advance(task)

            # Bindings
            if "bindings" in exports_to_run:
                task = progress.add_task("Exporting bindings...", total=1)
                handler = BindingHandler(client)
                data = handler.list()

                if detailed:
                    # Enrich with group and policy names
                    group_handler = GroupHandler(client)
                    policy_handler = PolicyHandler(client, level_type="account", level_id=client.account_uuid)

                    for binding in data:
                        group_uuid = binding.get("groupUuid", "")
                        policy_uuid = binding.get("policyUuid", "")

                        group = group_handler.get(group_uuid)
                        policy = policy_handler.get(policy_uuid)

                        binding["group_name"] = group.get("name", "") if group else ""
                        binding["policy_name"] = policy.get("name", "") if policy else ""

                file_path = export_dir / f"{prefix}_bindings.{ext}"
                write_data(data, file_path, format)
                exported_files.append(("bindings", len(data), file_path))
                progress.advance(task)

            # Boundaries
            if "boundaries" in exports_to_run:
                task = progress.add_task("Exporting boundaries...", total=1)
                handler = BoundaryHandler(client)
                data = handler.list()

                if detailed:
                    # Get full boundary details
                    detailed_data = []
                    for boundary in data:
                        boundary_id = boundary.get("uuid", "")
                        detail = handler.get(boundary_id)
                        if detail:
                            # Add attached policies
                            attached = handler.get_attached_policies(boundary_id)
                            detail["attached_policies"] = attached
                            detail["attached_policy_count"] = len(attached)
                            detailed_data.append(detail)
                        else:
                            detailed_data.append(boundary)
                    data = detailed_data

                file_path = export_dir / f"{prefix}_boundaries.{ext}"
                write_data(data, file_path, format)
                exported_files.append(("boundaries", len(data), file_path))
                progress.advance(task)

        # Summary
        console.print()
        console.print(f"[green]Export complete![/green]")
        console.print(f"Output directory: {export_dir}")
        console.print()

        for resource, count, path in exported_files:
            console.print(f"  {resource}: {count} records -> {path.name}")

    finally:
        client.close()


@app.command("group")
def export_group(
    identifier: str = typer.Argument(..., help="Group UUID or name"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
    format: str = typer.Option("yaml", "--format", "-f", help="Output format (yaml, json)"),
    include_members: bool = typer.Option(True, "--include-members/--no-members", help="Include member list"),
    include_policies: bool = typer.Option(True, "--include-policies/--no-policies", help="Include policy bindings"),
) -> None:
    """Export a single group with its details.

    Exports group definition in a format suitable for import/backup.
    """
    from dtiam.resources.groups import GroupHandler
    from dtiam.resources.bindings import BindingHandler
    from dtiam.resources.policies import PolicyHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    group_handler = GroupHandler(client)
    binding_handler = BindingHandler(client)
    policy_handler = PolicyHandler(client, level_type="account", level_id=client.account_uuid)

    try:
        # Get group
        group = group_handler.get(identifier)
        if not group:
            group = group_handler.get_by_name(identifier)

        if not group:
            console.print(f"[red]Error:[/red] Group '{identifier}' not found.")
            raise typer.Exit(1)

        group_uuid = group.get("uuid", "")
        group_name = group.get("name", "")

        export_data = {
            "apiVersion": "v1",
            "kind": "Group",
            "metadata": {
                "uuid": group_uuid,
                "exportedAt": datetime.now().isoformat(),
            },
            "spec": {
                "name": group_name,
                "description": group.get("description", ""),
            },
        }

        if include_members:
            members = group_handler.get_members(group_uuid)
            export_data["spec"]["members"] = [
                {"email": m.get("email", ""), "uid": m.get("uid", "")}
                for m in members
            ]

        if include_policies:
            bindings = binding_handler.get_for_group(group_uuid)
            policy_bindings = []
            for binding in bindings:
                policy_uuid = binding.get("policyUuid", "")
                policy = policy_handler.get(policy_uuid)
                policy_bindings.append({
                    "policyUuid": policy_uuid,
                    "policyName": policy.get("name", "") if policy else "",
                    "boundaryUuid": binding.get("boundaryUuid"),
                })
            export_data["spec"]["policyBindings"] = policy_bindings

        # Output
        if format == "json":
            output = json.dumps(export_data, indent=2)
        else:
            output = yaml.dump(export_data, default_flow_style=False)

        if output_file:
            output_file.write_text(output)
            console.print(f"[green]Exported[/green] group '{group_name}' to {output_file}")
        else:
            console.print(output)

    finally:
        client.close()


@app.command("policy")
def export_policy(
    identifier: str = typer.Argument(..., help="Policy UUID or name"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
    format: str = typer.Option("yaml", "--format", "-f", help="Output format (yaml, json)"),
    as_template: bool = typer.Option(False, "--as-template", "-t", help="Export as reusable template"),
) -> None:
    """Export a single policy with its details.

    With --as-template, exports in template format with variable placeholders.
    """
    from dtiam.resources.policies import PolicyHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = PolicyHandler(client, level_type="account", level_id=client.account_uuid)

    try:
        # Get policy
        policy = handler.get(identifier)
        if not policy:
            policy = handler.get_by_name(identifier)

        if not policy:
            console.print(f"[red]Error:[/red] Policy '{identifier}' not found.")
            raise typer.Exit(1)

        policy_name = policy.get("name", "")

        if as_template:
            # Export as template
            export_data = {
                "description": f"Template from policy: {policy_name}",
                "kind": "Policy",
                "template": {
                    "name": "{{ policy_name }}",
                    "description": policy.get("description", "{{ description | default('') }}"),
                    "statementQuery": policy.get("statementQuery", ""),
                },
            }
        else:
            export_data = {
                "apiVersion": "v1",
                "kind": "Policy",
                "metadata": {
                    "uuid": policy.get("uuid", ""),
                    "exportedAt": datetime.now().isoformat(),
                },
                "spec": {
                    "name": policy_name,
                    "description": policy.get("description", ""),
                    "statementQuery": policy.get("statementQuery", ""),
                },
            }

        # Output
        if format == "json":
            output = json.dumps(export_data, indent=2)
        else:
            output = yaml.dump(export_data, default_flow_style=False)

        if output_file:
            output_file.write_text(output)
            console.print(f"[green]Exported[/green] policy '{policy_name}' to {output_file}")
        else:
            console.print(output)

    finally:
        client.close()
