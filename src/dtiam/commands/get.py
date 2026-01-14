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
    app_columns,
    service_user_columns,
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
    level: Optional[str] = typer.Option(None, "--level", "-l", help="Policy level (account, global, environment, or env ID). Default: all levels"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List or get IAM policies.

    By default, lists policies from all levels (account, global, and environments).
    Use --level to filter to a specific level.
    """
    from dtiam.resources.policies import PolicyHandler
    from dtiam.resources.environments import EnvironmentHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        if identifier:
            # Try to find policy by UUID or name - search all levels
            handler = PolicyHandler(client, level_type="account", level_id=client.account_uuid)
            result = handler.get(identifier)
            if not result:
                result = handler.get_by_name(identifier)
            if not result:
                # Try global level
                handler = PolicyHandler(client, level_type="global", level_id="global")
                result = handler.get(identifier)
                if not result:
                    result = handler.get_by_name(identifier)
            if not result:
                console.print(f"[red]Error:[/red] Policy '{identifier}' not found.")
                raise typer.Exit(1)
            printer.print(result)
        else:
            # List policies
            results: list[dict] = []

            if level is None:
                # Query all levels: account, global, and environments
                # Account level
                handler = PolicyHandler(client, level_type="account", level_id=client.account_uuid)
                account_policies = handler.list()
                for p in account_policies:
                    p["_level"] = "account"
                results.extend(account_policies)

                # Global level (built-in policies)
                try:
                    handler = PolicyHandler(client, level_type="global", level_id="global")
                    global_policies = handler.list()
                    for p in global_policies:
                        p["_level"] = "global"
                    results.extend(global_policies)
                except Exception:
                    pass  # Global policies might not be accessible

                # Environment level - get all environments and query each
                try:
                    env_handler = EnvironmentHandler(client)
                    environments = env_handler.list()
                    for env in environments:
                        env_id = env.get("id")
                        if env_id:
                            try:
                                handler = PolicyHandler(client, level_type="environment", level_id=env_id)
                                env_policies = handler.list()
                                for p in env_policies:
                                    p["_level"] = f"environment:{env_id}"
                                results.extend(env_policies)
                            except Exception:
                                pass  # Some environments might not have policies
                except Exception:
                    pass  # Environments might not be accessible

            elif level == "global":
                handler = PolicyHandler(client, level_type="global", level_id="global")
                results = handler.list()
            elif level == "account":
                handler = PolicyHandler(client, level_type="account", level_id=client.account_uuid)
                results = handler.list()
            elif level == "environment":
                # All environments
                try:
                    env_handler = EnvironmentHandler(client)
                    environments = env_handler.list()
                    for env in environments:
                        env_id = env.get("id")
                        if env_id:
                            try:
                                handler = PolicyHandler(client, level_type="environment", level_id=env_id)
                                env_policies = handler.list()
                                for p in env_policies:
                                    p["_level"] = f"environment:{env_id}"
                                results.extend(env_policies)
                            except Exception:
                                pass
                except Exception:
                    pass
            else:
                # Specific environment ID
                handler = PolicyHandler(client, level_type="environment", level_id=level)
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
    level: Optional[str] = typer.Option(None, "--level", "-l", help="Binding level (account, global, environment, or env ID). Default: all levels"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List IAM policy bindings.

    By default, lists bindings from all levels (account, global, and environments).
    Use --level to filter to a specific level.
    """
    from dtiam.resources.bindings import BindingHandler
    from dtiam.resources.environments import EnvironmentHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        results: list[dict] = []

        if group_id:
            # When filtering by group, query all levels for that group
            handler = BindingHandler(client, level_type="account", level_id=client.account_uuid)
            results = handler.get_for_group(group_id)
        elif level is None:
            # Query all levels: account, global, and environments
            # Account level
            handler = BindingHandler(client, level_type="account", level_id=client.account_uuid)
            account_bindings = handler.list()
            for b in account_bindings:
                b["levelType"] = b.get("levelType", "account")
                b["levelId"] = b.get("levelId", client.account_uuid)
            results.extend(account_bindings)

            # Global level
            try:
                handler = BindingHandler(client, level_type="global", level_id="global")
                global_bindings = handler.list()
                for b in global_bindings:
                    b["levelType"] = b.get("levelType", "global")
                    b["levelId"] = b.get("levelId", "global")
                results.extend(global_bindings)
            except Exception:
                pass  # Global bindings might not be accessible

            # Environment level - get all environments and query each
            try:
                env_handler = EnvironmentHandler(client)
                environments = env_handler.list()
                for env in environments:
                    env_id = env.get("id")
                    if env_id:
                        try:
                            handler = BindingHandler(client, level_type="environment", level_id=env_id)
                            env_bindings = handler.list()
                            for b in env_bindings:
                                b["levelType"] = b.get("levelType", "environment")
                                b["levelId"] = b.get("levelId", env_id)
                            results.extend(env_bindings)
                        except Exception:
                            pass  # Some environments might not have bindings
            except Exception:
                pass  # Environments might not be accessible

        elif level == "global":
            handler = BindingHandler(client, level_type="global", level_id="global")
            results = handler.list()
        elif level == "account":
            handler = BindingHandler(client, level_type="account", level_id=client.account_uuid)
            results = handler.list()
        elif level == "environment":
            # All environments
            try:
                env_handler = EnvironmentHandler(client)
                environments = env_handler.list()
                for env in environments:
                    env_id = env.get("id")
                    if env_id:
                        try:
                            handler = BindingHandler(client, level_type="environment", level_id=env_id)
                            env_bindings = handler.list()
                            for b in env_bindings:
                                b["levelType"] = "environment"
                                b["levelId"] = env_id
                            results.extend(env_bindings)
                        except Exception:
                            pass
            except Exception:
                pass
        else:
            # Specific environment ID
            handler = BindingHandler(client, level_type="environment", level_id=level)
            results = handler.list()

        printer.print(results, binding_columns())
    finally:
        client.close()


@app.command("environments")
@app.command("envs")
@app.command("env")
def get_environments(
    identifier: Optional[str] = typer.Argument(None, help="Environment ID or name"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by name (partial match)"),
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
            if name:
                results = [e for e in results if name.lower() in e.get("name", "").lower()]
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


@app.command("apps")
@app.command("app")
def get_apps(
    identifier: Optional[str] = typer.Argument(None, help="App ID or name"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by name (partial match)"),
    environment: Optional[str] = typer.Option(
        None, "--environment", "-e", help="Environment ID or URL (e.g., abc12345 or abc12345.apps.dynatrace.com)"
    ),
    ids_only: bool = typer.Option(False, "--ids", help="Output only app IDs (for use in policies)"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List or get Dynatrace Apps from the App Engine Registry.

    App IDs can be used in policy/boundary statements like:
        shared:app-id = '{app.id}';

    Requires an environment URL. You can specify it via:
    - --environment flag with environment ID or full URL
    - DTIAM_ENVIRONMENT_URL environment variable
    """
    import os
    from dtiam.resources.apps import AppHandler
    from dtiam.resources.environments import EnvironmentHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        # Resolve environment URL
        env_url = environment or os.environ.get("DTIAM_ENVIRONMENT_URL")

        if not env_url:
            console.print("[red]Error:[/red] Environment required. Specify with --environment or DTIAM_ENVIRONMENT_URL")
            console.print("\nAvailable environments:")
            env_handler = EnvironmentHandler(client)
            envs = env_handler.list()
            for env in envs[:10]:
                console.print(f"  - {env.get('id')} ({env.get('name', 'unnamed')})")
            if len(envs) > 10:
                console.print(f"  ... and {len(envs) - 10} more")
            raise typer.Exit(1)

        # If just an environment ID, construct the full URL
        if not env_url.startswith("http") and "." not in env_url:
            env_url = f"https://{env_url}.apps.dynatrace.com"

        handler = AppHandler(client, env_url)

        if ids_only:
            # Output just the IDs for easy copy-paste into policies
            app_ids = handler.get_ids()
            if fmt in (OutputFormat.JSON, OutputFormat.PLAIN):
                printer.print(app_ids)
            else:
                for app_id in app_ids:
                    console.print(app_id)
        elif identifier:
            # Try to resolve by ID or name
            result = handler.get(identifier)
            if not result:
                result = handler.get_by_name(identifier)
            if not result:
                console.print(f"[red]Error:[/red] App '{identifier}' not found.")
                raise typer.Exit(1)
            printer.print(result)
        else:
            # List apps
            results = handler.list()
            if name:
                results = [a for a in results if name.lower() in a.get("name", "").lower()]
            printer.print(results, app_columns())
    finally:
        client.close()


@app.command("schemas")
@app.command("schema")
def get_schemas(
    identifier: Optional[str] = typer.Argument(None, help="Schema ID or display name"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by name (partial match on ID or display name)"),
    environment: Optional[str] = typer.Option(
        None, "--environment", "-e", help="Environment ID or URL (e.g., abc12345 or abc12345.live.dynatrace.com)"
    ),
    ids_only: bool = typer.Option(False, "--ids", help="Output only schema IDs (for use in boundaries)"),
    builtin_only: bool = typer.Option(False, "--builtin", help="Show only builtin schemas"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search by schema ID or display name (alias for --name)"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List or get Settings 2.0 schemas from the Environment API.

    Schema IDs can be used in boundary conditions like:
        settings:schemaId = "builtin:alerting.profile";

    Requires an environment URL and environment API token. You can specify via:
    - --environment flag with environment ID or full URL
    - DTIAM_ENVIRONMENT_URL environment variable
    - DTIAM_ENVIRONMENT_TOKEN environment variable (with settings.read scope)
    """
    import os
    from dtiam.resources.schemas import SchemaHandler
    from dtiam.resources.environments import EnvironmentHandler
    from dtiam.output import schema_columns

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        # Resolve environment URL
        env_url = environment or os.environ.get("DTIAM_ENVIRONMENT_URL")

        if not env_url:
            console.print("[red]Error:[/red] Environment required. Specify with --environment or DTIAM_ENVIRONMENT_URL")
            console.print("\nAvailable environments:")
            env_handler = EnvironmentHandler(client)
            envs = env_handler.list()
            for env in envs[:10]:
                console.print(f"  - {env.get('id')} ({env.get('name', 'unnamed')})")
            if len(envs) > 10:
                console.print(f"  ... and {len(envs) - 10} more")
            raise typer.Exit(1)

        # If just an environment ID, construct the full URL
        if not env_url.startswith("http") and "." not in env_url:
            env_url = f"https://{env_url}.live.dynatrace.com"

        handler = SchemaHandler(client, env_url)

        # Use name or search (search is alias for backward compatibility)
        filter_term = name or search

        if ids_only:
            # Output just the IDs for easy copy-paste into boundaries
            if builtin_only:
                schema_ids = handler.get_builtin_ids()
            else:
                schema_ids = handler.get_ids()
            if fmt in (OutputFormat.JSON, OutputFormat.PLAIN):
                printer.print(schema_ids)
            else:
                for schema_id in schema_ids:
                    console.print(schema_id)
        elif identifier:
            # Try to resolve by ID or name
            result = handler.get(identifier)
            if not result:
                result = handler.get_by_name(identifier)
            if not result:
                console.print(f"[red]Error:[/red] Schema '{identifier}' not found.")
                raise typer.Exit(1)
            printer.print(result)
        else:
            # List schemas
            results = handler.list()
            if builtin_only:
                results = [s for s in results if s.get("schemaId", "").startswith("builtin:")]
            if filter_term:
                # Filter by schema ID or display name
                results = handler.search(filter_term)
            printer.print(results, schema_columns())
    finally:
        client.close()


@app.command("service-users")
@app.command("service-user")
def get_service_users(
    identifier: Optional[str] = typer.Argument(None, help="Service user UUID or name"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by name (partial match)"),
    output: Optional[OutputFormat] = typer.Option(None, "-o", "--output"),
) -> None:
    """List or get IAM service users (OAuth clients).

    Service users are used for automation and API access.
    """
    from dtiam.resources.service_users import ServiceUserHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = ServiceUserHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        if identifier:
            # Try to resolve by UUID or name
            result = handler.get(identifier)
            if not result:
                result = handler.get_by_name(identifier)
            if not result:
                console.print(f"[red]Error:[/red] Service user '{identifier}' not found.")
                raise typer.Exit(1)
            printer.print(result)
        else:
            # List service users
            results = handler.list()
            if name:
                results = [s for s in results if name.lower() in s.get("name", "").lower()]
            printer.print(results, service_user_columns())
    finally:
        client.close()
