"""Template commands for IAM resource creation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from dtiam.client import create_client_from_config
from dtiam.config import load_config
from dtiam.output import OutputFormat, Printer
from dtiam.utils.templates import TemplateManager, TemplateRenderer, TemplateError

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


def parse_variables(var_strings: list[str]) -> dict[str, str]:
    """Parse variable strings in key=value format.

    Args:
        var_strings: List of "key=value" strings

    Returns:
        Dictionary of variable name to value
    """
    variables = {}
    for var_str in var_strings:
        if "=" not in var_str:
            raise ValueError(f"Invalid variable format: {var_str}. Use key=value")
        key, value = var_str.split("=", 1)
        variables[key.strip()] = value.strip()
    return variables


@app.command("list")
def list_templates(
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List all available templates."""
    manager = TemplateManager()
    templates = manager.list_templates()

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        printer.print(templates)
        return

    # Table output
    table = Table(title="Available Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Kind", style="green")
    table.add_column("Source", style="yellow")
    table.add_column("Description")

    for template in templates:
        table.add_row(
            template["name"],
            template["kind"],
            template["source"],
            template["description"],
        )

    console.print(table)


@app.command("show")
def show_template(
    name: str = typer.Argument(..., help="Template name"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Show a template definition and its required variables."""
    manager = TemplateManager()
    template_def = manager.get_template(name)

    if not template_def:
        console.print(f"[red]Error:[/red] Template '{name}' not found.")
        raise typer.Exit(1)

    fmt = output or get_output_format()

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        printer = Printer(format=fmt, plain=is_plain_mode())
        printer.print(template_def)
        return

    # Formatted output
    console.print()
    console.print(Panel(f"[bold]{name}[/bold]", subtitle=template_def.get("kind", "Unknown")))
    console.print(f"[dim]{template_def.get('description', 'No description')}[/dim]")
    console.print()

    # Show template content
    template_yaml = yaml.dump(template_def.get("template", {}), default_flow_style=False)
    syntax = Syntax(template_yaml, "yaml", theme="monokai", line_numbers=True)
    console.print("[bold]Template:[/bold]")
    console.print(syntax)
    console.print()

    # Show required variables
    variables = manager.get_template_variables(name)
    if variables:
        console.print("[bold]Variables:[/bold]")
        var_table = Table(show_header=True, header_style="dim")
        var_table.add_column("Name", style="cyan")
        var_table.add_column("Required", style="yellow")
        var_table.add_column("Default")

        for var in variables:
            has_default = "default" in var
            var_table.add_row(
                var["name"],
                "No" if has_default else "Yes",
                var.get("default", "-"),
            )

        console.print(var_table)
    else:
        console.print("[dim]No variables required[/dim]")

    console.print()


@app.command("render")
def render_template(
    name: str = typer.Argument(..., help="Template name"),
    var: list[str] = typer.Option([], "--var", "-v", help="Variable in key=value format"),
    var_file: Optional[Path] = typer.Option(None, "--var-file", "-f", help="YAML/JSON file with variables"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """Render a template with the given variables.

    Variables can be provided via:
    - Command line: --var key=value --var key2=value2
    - Variable file: --var-file variables.yaml

    Example:
        dtiam template render group-team --var team_name=platform
        dtiam template render manifest-team-setup --var-file vars.yaml
    """
    manager = TemplateManager()
    template_def = manager.get_template(name)

    if not template_def:
        console.print(f"[red]Error:[/red] Template '{name}' not found.")
        raise typer.Exit(1)

    # Collect variables
    variables = {}

    # Load from file first (if provided)
    if var_file:
        if not var_file.exists():
            console.print(f"[red]Error:[/red] Variable file not found: {var_file}")
            raise typer.Exit(1)

        content = var_file.read_text()
        if var_file.suffix in (".yaml", ".yml"):
            variables.update(yaml.safe_load(content) or {})
        elif var_file.suffix == ".json":
            variables.update(json.loads(content))
        else:
            console.print(f"[red]Error:[/red] Unsupported variable file format: {var_file.suffix}")
            raise typer.Exit(1)

    # Override with command line variables
    try:
        variables.update(parse_variables(var))
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Render the template
    try:
        rendered = manager.render_template(name, variables)
    except TemplateError as e:
        console.print(f"[red]Error:[/red] {e}")

        # Show available variables
        template_vars = manager.get_template_variables(name)
        if template_vars:
            console.print()
            console.print("[yellow]Required variables:[/yellow]")
            for v in template_vars:
                default_str = f" (default: {v['default']})" if "default" in v else " [required]"
                console.print(f"  --var {v['name']}=<value>{default_str}")

        raise typer.Exit(1)

    fmt = output or get_output_format()

    if fmt == OutputFormat.JSON:
        console.print(json.dumps(rendered, indent=2))
    else:
        console.print(yaml.dump(rendered, default_flow_style=False))


@app.command("apply")
def apply_template(
    name: str = typer.Argument(..., help="Template name"),
    var: list[str] = typer.Option([], "--var", "-v", help="Variable in key=value format"),
    var_file: Optional[Path] = typer.Option(None, "--var-file", "-f", help="YAML/JSON file with variables"),
) -> None:
    """Render a template and create the resource.

    Example:
        dtiam template apply group-team --var team_name=platform
        dtiam template apply policy-readonly --var env_name=production
    """
    manager = TemplateManager()
    template_def = manager.get_template(name)

    if not template_def:
        console.print(f"[red]Error:[/red] Template '{name}' not found.")
        raise typer.Exit(1)

    # Collect variables
    variables = {}

    if var_file:
        if not var_file.exists():
            console.print(f"[red]Error:[/red] Variable file not found: {var_file}")
            raise typer.Exit(1)

        content = var_file.read_text()
        if var_file.suffix in (".yaml", ".yml"):
            variables.update(yaml.safe_load(content) or {})
        elif var_file.suffix == ".json":
            variables.update(json.loads(content))

    try:
        variables.update(parse_variables(var))
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Render the template
    try:
        rendered = manager.render_template(name, variables)
    except TemplateError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    kind = rendered.get("kind", "").lower()
    spec = rendered.get("spec", {})

    if is_dry_run():
        console.print("[yellow]Dry-run mode:[/yellow] Would create:")
        console.print(yaml.dump(rendered, default_flow_style=False))
        return

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    try:
        if kind == "group":
            from dtiam.resources.groups import GroupHandler
            handler = GroupHandler(client)
            result = handler.create(spec)
            console.print(f"[green]Created group:[/green] {result.get('name')}")

        elif kind == "policy":
            from dtiam.resources.policies import PolicyHandler
            handler = PolicyHandler(client, level_type="account", level_id=client.account_uuid)
            result = handler.create(spec)
            console.print(f"[green]Created policy:[/green] {result.get('name')}")

        elif kind == "boundary":
            from dtiam.resources.boundaries import BoundaryHandler
            handler = BoundaryHandler(client)
            result = handler.create(spec)
            console.print(f"[green]Created boundary:[/green] {result.get('name')}")

        elif kind == "binding":
            from dtiam.resources.bindings import BindingHandler
            from dtiam.resources.groups import GroupHandler
            from dtiam.resources.policies import PolicyHandler

            group_handler = GroupHandler(client)
            policy_handler = PolicyHandler(client, level_type="account", level_id=client.account_uuid)
            binding_handler = BindingHandler(client)

            # Resolve group
            group_id = spec.get("group", "")
            group = group_handler.get(group_id) or group_handler.get_by_name(group_id)
            if not group:
                console.print(f"[red]Error:[/red] Group not found: {group_id}")
                raise typer.Exit(1)

            # Resolve policy
            policy_id = spec.get("policy", "")
            policy = policy_handler.get(policy_id) or policy_handler.get_by_name(policy_id)
            if not policy:
                console.print(f"[red]Error:[/red] Policy not found: {policy_id}")
                raise typer.Exit(1)

            # Optional boundary
            boundaries = []
            if spec.get("boundary"):
                boundaries = [spec["boundary"]]

            result = binding_handler.create(
                group_uuid=group.get("uuid"),
                policy_uuid=policy.get("uuid"),
                boundaries=boundaries,
            )
            console.print(f"[green]Created binding:[/green] {group.get('name')} -> {policy.get('name')}")

        elif kind == "manifest" or kind == "list":
            # Handle multi-resource manifests
            items = spec.get("items", []) if kind == "list" else rendered.get("items", [])
            for item in items:
                item_kind = item.get("kind", "").lower()
                item_spec = item.get("spec", {})

                if item_kind == "group":
                    from dtiam.resources.groups import GroupHandler
                    handler = GroupHandler(client)
                    result = handler.create(item_spec)
                    console.print(f"[green]Created group:[/green] {result.get('name')}")

                elif item_kind == "policy":
                    from dtiam.resources.policies import PolicyHandler
                    handler = PolicyHandler(client, level_type="account", level_id=client.account_uuid)
                    result = handler.create(item_spec)
                    console.print(f"[green]Created policy:[/green] {result.get('name')}")

                elif item_kind == "binding":
                    from dtiam.resources.bindings import BindingHandler
                    from dtiam.resources.groups import GroupHandler
                    from dtiam.resources.policies import PolicyHandler

                    group_handler = GroupHandler(client)
                    policy_handler = PolicyHandler(client, level_type="account", level_id=client.account_uuid)
                    binding_handler = BindingHandler(client)

                    group_id = item_spec.get("group", "")
                    group = group_handler.get(group_id) or group_handler.get_by_name(group_id)
                    if not group:
                        console.print(f"[yellow]Warning:[/yellow] Group not found: {group_id}, skipping binding")
                        continue

                    policy_id = item_spec.get("policy", "")
                    policy = policy_handler.get(policy_id) or policy_handler.get_by_name(policy_id)
                    if not policy:
                        console.print(f"[yellow]Warning:[/yellow] Policy not found: {policy_id}, skipping binding")
                        continue

                    boundaries = [item_spec["boundary"]] if item_spec.get("boundary") else []
                    result = binding_handler.create(
                        group_uuid=group.get("uuid"),
                        policy_uuid=policy.get("uuid"),
                        boundaries=boundaries,
                    )
                    console.print(f"[green]Created binding:[/green] {group.get('name')} -> {policy.get('name')}")

        else:
            console.print(f"[red]Error:[/red] Unknown resource kind: {kind}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to create resource: {e}")
        raise typer.Exit(1)

    finally:
        client.close()


@app.command("save")
def save_template(
    name: str = typer.Argument(..., help="Template name"),
    kind: str = typer.Option(..., "--kind", "-k", help="Resource kind (Group, Policy, Boundary, Binding)"),
    file: Path = typer.Option(..., "--file", "-f", help="YAML/JSON file with template definition"),
    description: str = typer.Option("", "--description", "-d", help="Template description"),
) -> None:
    """Save a custom template.

    The template file should contain the template definition with {{ variable }} placeholders.

    Example template file (group.yaml):
        name: "{{ group_name }}"
        description: "{{ description | default('') }}"
    """
    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)

    content = file.read_text()
    if file.suffix in (".yaml", ".yml"):
        template = yaml.safe_load(content)
    elif file.suffix == ".json":
        template = json.loads(content)
    else:
        console.print(f"[red]Error:[/red] Unsupported file format: {file.suffix}")
        raise typer.Exit(1)

    manager = TemplateManager()

    # Check if it would override a builtin
    if name in manager.BUILTIN_TEMPLATES:
        console.print(f"[red]Error:[/red] Cannot override built-in template: {name}")
        raise typer.Exit(1)

    file_path = manager.save_template(name, kind, template, description)
    console.print(f"[green]Saved template:[/green] {name} -> {file_path}")


@app.command("delete")
def delete_template(
    name: str = typer.Argument(..., help="Template name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a custom template."""
    manager = TemplateManager()

    if name in manager.BUILTIN_TEMPLATES:
        console.print(f"[red]Error:[/red] Cannot delete built-in template: {name}")
        raise typer.Exit(1)

    template_def = manager.get_template(name)
    if not template_def:
        console.print(f"[red]Error:[/red] Template '{name}' not found.")
        raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(f"Delete template '{name}'?")
        if not confirm:
            console.print("Aborted.")
            raise typer.Exit(0)

    if manager.delete_template(name):
        console.print(f"[green]Deleted template:[/green] {name}")
    else:
        console.print(f"[red]Error:[/red] Failed to delete template '{name}'")
        raise typer.Exit(1)


@app.command("path")
def show_templates_path() -> None:
    """Show the path where custom templates are stored."""
    manager = TemplateManager()
    console.print(f"Templates directory: {manager.templates_dir}")
