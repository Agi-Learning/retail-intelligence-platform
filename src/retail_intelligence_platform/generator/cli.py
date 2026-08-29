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
from retail_intelligence_platform.generator.loaders.catalog import (
    load_catalog as load_catalog_records,
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


_PROTECTED_PROFILES = frozenset(
    {
        "medium",
        "large",
        "stress",
    }
)


@app.command("load-catalog")
def load_catalog_command(
    profile_name: Annotated[
        str | None,
        typer.Option(
            "--profile",
            "-p",
            help="Generation profile name.",
        ),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            help=("Acknowledge execution of a large generation profile."),
        ),
    ] = False,
) -> None:
    """Load deterministic catalogue records."""

    settings, profile = resolve_profile(profile_name)

    if profile.name in _PROTECTED_PROFILES and not yes:
        console.print("[bold yellow]Execution blocked.[/bold yellow]")
        console.print(
            f"Profile {profile.name!r} is protected "
            f"and estimates "
            f"{profile.estimated_total_rows:,} rows."
        )
        console.print("Review the plan, then rerun with --yes.")

        raise typer.Exit(code=2)

    console.print(f"[bold]Catalogue profile:[/bold] {profile.name}")
    console.print(
        f"[bold]Expected catalogue rows:[/bold] "
        f"{profile.brand_count:,} brands, "
        f"{profile.category_count:,} categories, "
        f"{profile.product_count:,} products, "
        f"{profile.product_count * profile.prices_per_product:,} "
        "prices"
    )

    try:
        check_database(settings)

        result = load_catalog_records(
            settings,
            profile,
        )
    except Exception as error:
        console.print(f"[bold red]Catalogue load failed:[/bold red] {error}")

        raise typer.Exit(code=1) from error

    console.print("[bold green]Catalogue load completed[/bold green]")
    console.print(f"Brands: {result.brands:,}")
    console.print(f"Categories: {result.categories:,}")
    console.print(f"Products: {result.products:,}")
    console.print(f"Product prices: {result.product_prices:,}")
    console.print(f"Total catalogue rows: {result.total_rows:,}")


if __name__ == "__main__":
    app()
