"""Cache management commands."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from dtiam.utils.cache import cache

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("stats")
def show_stats() -> None:
    """Show cache statistics.

    Displays hit/miss rates and entry counts.
    """
    stats = cache.stats()

    console.print()
    console.print("[bold]Cache Statistics[/bold]")
    console.print()

    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="cyan")
    table.add_column("Value")

    table.add_row("Active entries", str(stats["active_entries"]))
    table.add_row("Expired entries", str(stats["expired_entries"]))
    table.add_row("Total entries", str(stats["total_entries"]))
    table.add_row("Cache hits", str(stats["hits"]))
    table.add_row("Cache misses", str(stats["misses"]))
    table.add_row("Hit rate", f"{stats['hit_rate']}%")
    table.add_row("Default TTL", f"{stats['default_ttl']} seconds")

    console.print(table)


@app.command("clear")
def clear_cache(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    expired_only: bool = typer.Option(False, "--expired-only", "-e", help="Only clear expired entries"),
    prefix: str = typer.Option("", "--prefix", "-p", help="Only clear entries with this prefix"),
) -> None:
    """Clear cache entries.

    Examples:
        dtiam cache clear                    # Clear all entries
        dtiam cache clear --expired-only     # Clear only expired entries
        dtiam cache clear --prefix groups    # Clear entries starting with 'groups'
    """
    if expired_only:
        count = cache.clear_expired()
        console.print(f"[green]Cleared {count} expired cache entries.[/green]")
        return

    if prefix:
        if not force:
            confirm = typer.confirm(f"Clear all cache entries with prefix '{prefix}'?")
            if not confirm:
                console.print("Aborted.")
                raise typer.Exit(0)

        count = cache.clear_prefix(prefix)
        console.print(f"[green]Cleared {count} cache entries with prefix '{prefix}'.[/green]")
        return

    # Clear all
    if not force:
        stats = cache.stats()
        confirm = typer.confirm(f"Clear all {stats['total_entries']} cache entries?")
        if not confirm:
            console.print("Aborted.")
            raise typer.Exit(0)

    count = cache.clear()
    console.print(f"[green]Cleared {count} cache entries.[/green]")


@app.command("keys")
def list_keys(
    prefix: str = typer.Option("", "--prefix", "-p", help="Filter by prefix"),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum keys to show"),
) -> None:
    """List cache keys.

    Shows all keys currently in the cache.
    """
    keys = cache.keys()

    if prefix:
        keys = [k for k in keys if k.startswith(prefix)]

    console.print(f"\n[bold]Cache Keys[/bold] ({len(keys)} total)\n")

    if not keys:
        console.print("[yellow]No keys found.[/yellow]")
        return

    for key in keys[:limit]:
        console.print(f"  {key}")

    if len(keys) > limit:
        console.print(f"\n  ... and {len(keys) - limit} more")


@app.command("reset-stats")
def reset_stats() -> None:
    """Reset cache hit/miss statistics."""
    cache.reset_stats()
    console.print("[green]Cache statistics reset.[/green]")


@app.command("set-ttl")
def set_ttl(
    seconds: int = typer.Argument(..., help="Default TTL in seconds"),
) -> None:
    """Set the default cache TTL.

    This affects new cache entries. Existing entries keep their original TTL.
    """
    if seconds < 0:
        console.print("[red]Error:[/red] TTL must be non-negative.")
        raise typer.Exit(1)

    cache.default_ttl = seconds
    console.print(f"[green]Default cache TTL set to {seconds} seconds.[/green]")
