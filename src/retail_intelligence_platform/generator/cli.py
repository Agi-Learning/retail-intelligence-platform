"""Command-line interface for retail source-data generation."""

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from retail_intelligence_platform.generator.config import (
    GeneratorSettings,
)
from retail_intelligence_platform.generator.database import (
    check_database,
)
from retail_intelligence_platform.generator.profiles import (
    available_profiles,
    get_profile,
)

app = typer.Typer(
    name="retail-data",
    help="Generate deterministic retail source-system data.",
    no_args_is_help=True,
)

console = Console()


def resolve_profile(profile_name: str | None):
    """Resolve a CLI profile override or environment default."""

    settings = GeneratorSettings()
    selected_name = profile_name or settings.profile

    try:
        profile = get_profile(selected_name)
    except ValueError as error:
        raise typer.BadParameter(
            str(error),
            param_hint="--profile",
        ) from error

    return settings, profile


@app.command()
def validate() -> None:
    """Validate configuration and PostgreSQL connectivity."""

    settings = GeneratorSettings()

    try:
        health = check_database(settings)
    except Exception as error:
        console.print(f"[bold red]Database validation failed:[/bold red] {error}")
        raise typer.Exit(code=1) from error

    console.print("[bold green]Database validation passed[/bold green]")
    console.print(f"Connection: {settings.safe_connection_label}")
    console.print(f"Database: {health.database}")
    console.print(f"Runtime role: {health.user}")
    console.print(f"Timezone: {health.timezone}")
    console.print(f"PostgreSQL version number: {health.server_version_number}")
    console.print(f"Required tables: {len(health.required_tables)}")
    console.print(
        f"Audit access: "
        f"insert={health.audit_insert_allowed}, "
        f"select={health.audit_select_allowed}"
    )


@app.command()
def plan(
    profile_name: Annotated[
        str | None,
        typer.Option(
            "--profile",
            "-p",
            help="Generation profile name.",
        ),
    ] = None,
) -> None:
    """Display the deterministic generation plan."""

    settings, profile = resolve_profile(profile_name)

    console.print(f"[bold]Profile:[/bold] {profile.name}")
    console.print(f"[bold]Seed:[/bold] {settings.seed}")
    console.print(f"[bold]Batch size:[/bold] {settings.batch_size:,}")

    table = Table(
        title="Estimated generated rows",
        show_header=True,
    )

    table.add_column("Table", style="cyan")
    table.add_column(
        "Rows",
        justify="right",
        style="green",
    )

    for table_name, row_count in profile.estimated_rows.items():
        table.add_row(
            table_name,
            f"{row_count:,}",
        )

    table.add_section()
    table.add_row(
        "TOTAL",
        f"{profile.estimated_total_rows:,}",
        style="bold",
    )

    console.print(table)


@app.command("profiles")
def list_profiles() -> None:
    """List available generation profiles."""

    table = Table(
        title="Generation profiles",
        show_header=True,
    )

    table.add_column("Profile", style="cyan")
    table.add_column("Estimated rows", justify="right")

    for profile_name in available_profiles():
        profile = get_profile(profile_name)

        table.add_row(
            profile.name,
            f"{profile.estimated_total_rows:,}",
        )

    console.print(table)


if __name__ == "__main__":
    app()
