"""Platform token management commands for IAM operations."""

from __future__ import annotations

from pathlib import Path

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


def get_output_format() -> OutputFormat:
    """Get output format from CLI state."""
    from dtiam.cli import state
    return state.output


def is_plain_mode() -> bool:
    """Check if plain mode is enabled."""
    from dtiam.cli import state
    return state.plain


@app.command("list")
def list_platform_tokens(
    name: str | None = typer.Option(None, "--name", "-n", help="Filter by token name (partial match)"),
    output: OutputFormat | None = typer.Option(None, "-o", "--output"),
) -> None:
    """List all platform tokens in the account.

    Requires the `platform-token:tokens:manage` scope.

    Example:
        dtiam platform-token list
        dtiam platform-token list -o json
        dtiam platform-token list --name "CI"
    """
    from dtiam.output import platform_token_columns
    from dtiam.resources.platform_tokens import PlatformTokenHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = PlatformTokenHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        tokens = handler.list()

        # Apply name filter if provided
        if name:
            tokens = [t for t in tokens if name.lower() in t.get("name", "").lower()]

        if not tokens:
            console.print("No platform tokens found.")
            return

        printer.print(tokens, platform_token_columns())

    finally:
        client.close()


@app.command("get")
def get_platform_token(
    token: str = typer.Argument(..., help="Platform token ID or name"),
    output: OutputFormat | None = typer.Option(None, "-o", "--output"),
) -> None:
    """Get details of a platform token.

    Example:
        dtiam platform-token get my-token
        dtiam platform-token get abc-123-def -o json
    """
    from dtiam.commands.describe import print_detail_view
    from dtiam.resources.platform_tokens import PlatformTokenHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = PlatformTokenHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        # Try by ID first, then by name
        token_obj = handler.get(token)
        if not token_obj:
            token_obj = handler.get_by_name(token)

        if not token_obj:
            console.print(f"[red]Error:[/red] Platform token '{token}' not found.")
            raise typer.Exit(1)

        if output:
            printer.print(token_obj)
        else:
            print_detail_view(token_obj, f"Platform Token: {token_obj.get('name', token)}")

    finally:
        client.close()


@app.command("create")
def create_platform_token(
    name: str = typer.Option(..., "--name", "-n", help="Token name/description"),
    scopes: str | None = typer.Option(
        None, "--scopes", "-s",
        help="Comma-separated list of scopes for the token"
    ),
    expires_in: str | None = typer.Option(
        None, "--expires-in", "-e",
        help="Token expiration (e.g., '30d', '1y', '365d')"
    ),
    output: OutputFormat | None = typer.Option(None, "-o", "--output"),
    save_token: Path | None = typer.Option(
        None, "--save-token",
        help="Save token value to file"
    ),
) -> None:
    """Generate a new platform token.

    Creates a platform token and returns the token value.
    IMPORTANT: Save the token value - it cannot be retrieved later!

    Requires the `platform-token:tokens:manage` scope.

    Example:
        dtiam platform-token create --name "CI Pipeline Token"
        dtiam platform-token create --name "Automation" --expires-in 30d
        dtiam platform-token create --name "CI Token" --save-token token.txt
        dtiam platform-token create --name "Custom" --scopes "account-idm-read,account-env-read"
    """
    from dtiam.resources.platform_tokens import PlatformTokenHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = PlatformTokenHandler(client)

    fmt = output or get_output_format()
    printer = Printer(format=fmt, plain=is_plain_mode())

    try:
        # Parse scopes if provided
        scope_list: list[str] | None = None
        if scopes:
            scope_list = [s.strip() for s in scopes.split(",") if s.strip()]

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would create platform token '{name}'")
            if scope_list:
                console.print(f"  Scopes: {', '.join(scope_list)}")
            if expires_in:
                console.print(f"  Expires in: {expires_in}")
            return

        result = handler.create(
            name=name,
            scopes=scope_list,
            expires_in=expires_in,
        )

        if result:
            console.print(f"[green]Created platform token:[/green] {name}")

            # Get the token value - check various possible field names
            token_value = result.get("token", result.get("value", result.get("tokenValue", "")))

            if token_value:
                console.print("")
                console.print("[yellow]IMPORTANT: Save this token now![/yellow]")
                console.print("[yellow]The token value cannot be retrieved later.[/yellow]")
                console.print("")
                console.print(f"Token: {token_value}")

                if save_token:
                    save_token.write_text(token_value)
                    console.print(f"\n[green]Token saved to:[/green] {save_token}")

            # Print full result for structured output
            if fmt in (OutputFormat.JSON, OutputFormat.YAML):
                printer.print(result)
        else:
            console.print(f"[red]Error:[/red] Failed to create platform token '{name}'")
            raise typer.Exit(1)

    finally:
        client.close()


@app.command("delete")
def delete_platform_token(
    token: str = typer.Argument(..., help="Platform token ID or name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a platform token.

    This will immediately revoke the token and any applications using it
    will no longer be able to authenticate.

    Example:
        dtiam platform-token delete abc-123-def
        dtiam platform-token delete "CI Pipeline Token"
        dtiam platform-token delete abc-123 --force
    """
    from dtiam.resources.platform_tokens import PlatformTokenHandler

    config = load_config()
    client = create_client_from_config(config, get_context(), is_verbose())
    handler = PlatformTokenHandler(client)

    try:
        # Resolve token (by ID or name)
        token_obj = handler.get(token)
        if not token_obj:
            token_obj = handler.get_by_name(token)

        if not token_obj:
            console.print(f"[red]Error:[/red] Platform token '{token}' not found.")
            raise typer.Exit(1)

        token_id = token_obj.get("id", "")
        token_name = token_obj.get("name", token)

        if is_dry_run():
            console.print(f"[yellow]Dry-run mode:[/yellow] Would delete platform token '{token_name}'")
            return

        if not force:
            confirm = typer.confirm(
                f"Delete platform token '{token_name}'? "
                "Applications using this token will lose access."
            )
            if not confirm:
                console.print("Aborted.")
                raise typer.Exit(0)

        success = handler.delete(token_id)

        if success:
            console.print(f"[green]Deleted platform token:[/green] {token_name}")
        else:
            console.print(f"[red]Error:[/red] Failed to delete platform token '{token_name}'")
            raise typer.Exit(1)

    finally:
        client.close()
