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
from retail_intelligence_platform.generator.loaders.commerce import (
    load_commerce as load_commerce_records,
)
from retail_intelligence_platform.generator.loaders.events import (
    load_events as load_event_records,
)
from retail_intelligence_platform.generator.loaders.identity import (
    load_identity as load_identity_records,
)
from retail_intelligence_platform.generator.loaders.inventory import (
    load_inventory as load_inventory_records,
)
from retail_intelligence_platform.generator.loaders.orders import (
    load_orders as load_order_records,
)
from retail_intelligence_platform.generator.loaders.payments import (
    load_payments as load_payment_records,
)
from retail_intelligence_platform.generator.loaders.reservations import (
    load_reservations as load_reservation_records,
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


def require_profile_confirmation(
    profile,
    confirmed: bool,
) -> None:
    """Block expensive profiles without explicit consent."""

    if profile.name not in _PROTECTED_PROFILES or confirmed:
        return

    console.print("[bold yellow]Execution blocked.[/bold yellow]")
    console.print(
        f"Profile {profile.name!r} is protected "
        f"and estimates "
        f"{profile.estimated_total_rows:,} rows."
    )
    console.print("Review the plan, then rerun with --yes.")

    raise typer.Exit(code=2)


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

    require_profile_confirmation(profile, yes)

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


@app.command("load-inventory")
def load_inventory_command(
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
    """Load warehouses and product stock."""

    settings, profile = resolve_profile(profile_name)
    require_profile_confirmation(profile, yes)

    expected_stock = profile.product_count * profile.warehouses_per_product

    console.print(f"[bold]Inventory profile:[/bold] {profile.name}")
    console.print(
        f"[bold]Expected inventory rows:[/bold] "
        f"{profile.warehouse_count:,} warehouses, "
        f"{expected_stock:,} stock rows"
    )

    try:
        check_database(settings)

        result = load_inventory_records(
            settings,
            profile,
        )
    except Exception as error:
        console.print(f"[bold red]Inventory load failed:[/bold red] {error}")

        raise typer.Exit(code=1) from error

    console.print("[bold green]Inventory load completed[/bold green]")
    console.print(f"Warehouses: {result.warehouses:,}")
    console.print(f"Stock rows: {result.stock:,}")
    console.print(f"Reorder required: {result.reorder_required:,}")
    console.print(f"Total inventory rows: {result.total_rows:,}")


@app.command("load-identity")
def load_identity_command(
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
    """Load customers, credentials and addresses."""

    settings, profile = resolve_profile(profile_name)
    require_profile_confirmation(profile, yes)

    expected_addresses = profile.customer_count * profile.addresses_per_customer

    console.print(f"[bold]Identity profile:[/bold] {profile.name}")
    console.print(
        f"[bold]Expected identity rows:[/bold] "
        f"{profile.customer_count:,} customers, "
        f"{profile.customer_count:,} credentials, "
        f"{expected_addresses:,} addresses"
    )

    try:
        check_database(settings)

        result = load_identity_records(
            settings,
            profile,
        )
    except Exception as error:
        console.print(f"[bold red]Identity load failed:[/bold red] {error}")

        raise typer.Exit(code=1) from error

    console.print("[bold green]Identity load completed[/bold green]")
    console.print(f"Customers: {result.customers:,}")
    console.print(f"Credentials: {result.credentials:,}")
    console.print(f"Addresses: {result.addresses:,}")
    console.print(f"Default addresses: {result.default_addresses:,}")
    console.print(f"Total identity rows: {result.total_rows:,}")


@app.command("load-foundation")
def load_foundation_command(
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
    """Load identity, catalogue and inventory."""

    settings, profile = resolve_profile(profile_name)
    require_profile_confirmation(profile, yes)

    console.print(f"[bold]Foundation profile:[/bold] {profile.name}")

    try:
        check_database(settings)

        console.print("[bold]Stage 1/3:[/bold] Identity")
        identity_result = load_identity_records(
            settings,
            profile,
        )

        console.print("[bold]Stage 2/3:[/bold] Catalogue")
        catalog_result = load_catalog_records(
            settings,
            profile,
        )

        console.print("[bold]Stage 3/3:[/bold] Inventory")
        inventory_result = load_inventory_records(
            settings,
            profile,
        )
    except Exception as error:
        console.print(f"[bold red]Foundation load failed:[/bold red] {error}")

        raise typer.Exit(code=1) from error

    total_rows = (
        identity_result.total_rows
        + catalog_result.total_rows
        + inventory_result.total_rows
    )

    console.print("[bold green]Foundation load completed[/bold green]")
    console.print(f"Identity rows: {identity_result.total_rows:,}")
    console.print(f"Catalogue rows: {catalog_result.total_rows:,}")
    console.print(f"Inventory rows: {inventory_result.total_rows:,}")
    console.print(f"Foundation total: {total_rows:,}")


@app.command("load-all")
def load_all_command(
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
    """Load the complete source-system dataset."""

    settings, profile = resolve_profile(profile_name)
    require_profile_confirmation(profile, yes)

    console.print(f"[bold]Complete load profile:[/bold] {profile.name}")
    console.print(f"[bold]Estimated rows:[/bold] {profile.estimated_total_rows:,}")

    try:
        check_database(settings)

        console.print("[bold]Stage 1/8:[/bold] Identity")
        identity_result = load_identity_records(
            settings,
            profile,
        )

        console.print("[bold]Stage 2/8:[/bold] Catalogue")
        catalog_result = load_catalog_records(
            settings,
            profile,
        )

        console.print("[bold]Stage 3/8:[/bold] Inventory")
        inventory_result = load_inventory_records(
            settings,
            profile,
        )

        console.print("[bold]Stage 4/8:[/bold] Shopping carts")
        commerce_result = load_commerce_records(
            settings,
            profile,
        )

        console.print("[bold]Stage 5/8:[/bold] Orders")
        order_result = load_order_records(
            settings,
            profile,
        )

        console.print("[bold]Stage 6/8:[/bold] Inventory reservations")
        reservation_result = load_reservation_records(
            settings,
            profile,
        )

        console.print("[bold]Stage 7/8:[/bold] Payments")
        payment_result = load_payment_records(
            settings,
            profile,
        )

        console.print("[bold]Stage 8/8:[/bold] Outbox and audit events")
        event_result = load_event_records(
            settings,
            profile,
        )
    except Exception as error:
        console.print(f"[bold red]Complete load failed:[/bold red] {error}")

        raise typer.Exit(code=1) from error

    total_rows = (
        identity_result.total_rows
        + catalog_result.total_rows
        + inventory_result.total_rows
        + commerce_result.total_rows
        + order_result.total_rows
        + reservation_result.reservations
        + payment_result.total_rows
        + event_result.total_generated_rows
    )

    console.print("[bold green]Complete load finished[/bold green]")
    console.print(f"Identity rows: {identity_result.total_rows:,}")
    console.print(f"Catalogue rows: {catalog_result.total_rows:,}")
    console.print(f"Inventory rows: {inventory_result.total_rows:,}")
    console.print(f"Shopping-cart rows: {commerce_result.total_rows:,}")
    console.print(f"Order rows: {order_result.total_rows:,}")
    console.print(f"Reservation rows: {reservation_result.reservations:,}")
    console.print(f"Payment rows: {payment_result.total_rows:,}")
    console.print(f"Event rows: {event_result.total_generated_rows:,}")
    console.print(f"[bold]Complete total:[/bold] {total_rows:,}")

    if total_rows != profile.estimated_total_rows:
        console.print(
            "[bold red]Generated total does not match the profile estimate.[/bold red]"
        )
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
