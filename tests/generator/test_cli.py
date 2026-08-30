from decimal import Decimal

from typer.testing import CliRunner

import retail_intelligence_platform.generator.cli as cli_module
from retail_intelligence_platform.generator.cli import app
from retail_intelligence_platform.generator.loaders.catalog import (
    CatalogLoadResult,
)
from retail_intelligence_platform.generator.loaders.commerce import (
    CommerceLoadResult,
)
from retail_intelligence_platform.generator.loaders.events import (
    EventLoadResult,
)
from retail_intelligence_platform.generator.loaders.identity import (
    IdentityLoadResult,
)
from retail_intelligence_platform.generator.loaders.inventory import (
    InventoryLoadResult,
)
from retail_intelligence_platform.generator.loaders.orders import (
    OrderLoadResult,
)
from retail_intelligence_platform.generator.loaders.payments import (
    PaymentLoadResult,
)
from retail_intelligence_platform.generator.loaders.reservations import (
    ReservationLoadResult,
)

runner = CliRunner()


def test_cli_displays_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Generate deterministic retail" in result.stdout
    assert "validate" in result.stdout
    assert "plan" in result.stdout
    assert "profiles" in result.stdout


def test_profiles_command_lists_profiles() -> None:
    result = runner.invoke(app, ["profiles"])

    assert result.exit_code == 0
    assert "smoke" in result.stdout
    assert "small" in result.stdout
    assert "medium" in result.stdout
    assert "large" in result.stdout
    assert "stress" in result.stdout


def test_smoke_plan_displays_total() -> None:
    result = runner.invoke(
        app,
        ["plan", "--profile", "smoke"],
    )

    assert result.exit_code == 0
    assert "Profile: smoke" in result.stdout
    assert "identity.customers" in result.stdout
    assert "commerce.orders" in result.stdout
    assert "3,046" in result.stdout


def test_unknown_profile_fails_safely() -> None:
    result = runner.invoke(
        app,
        ["plan", "--profile", "unknown"],
    )

    assert result.exit_code != 0
    assert "Unknown profile" in result.output


def test_large_catalogue_load_requires_yes() -> None:
    result = runner.invoke(
        app,
        [
            "load-catalog",
            "--profile",
            "large",
        ],
    )

    assert result.exit_code == 2
    assert "Execution blocked" in result.stdout
    assert "rerun with --yes" in result.stdout


def test_large_catalogue_load_with_yes_executes(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        cli_module,
        "check_database",
        lambda settings: None,
    )

    monkeypatch.setattr(
        cli_module,
        "load_catalog_records",
        lambda settings, profile: CatalogLoadResult(
            brands=1_000,
            categories=2_500,
            products=200_000,
            product_prices=400_000,
        ),
    )

    result = runner.invoke(
        app,
        [
            "load-catalog",
            "--profile",
            "large",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    assert "Catalogue load completed" in result.stdout
    assert "Products: 200,000" in result.stdout


def test_smoke_catalogue_load_does_not_require_yes(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        cli_module,
        "check_database",
        lambda settings: None,
    )

    monkeypatch.setattr(
        cli_module,
        "load_catalog_records",
        lambda settings, profile: CatalogLoadResult(
            brands=5,
            categories=10,
            products=50,
            product_prices=100,
        ),
    )

    result = runner.invoke(
        app,
        [
            "load-catalog",
            "--profile",
            "smoke",
        ],
    )

    assert result.exit_code == 0
    assert "Catalogue load completed" in result.stdout
    assert "Total catalogue rows: 165" in result.stdout


def test_catalogue_loader_failure_is_safe(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        cli_module,
        "check_database",
        lambda settings: None,
    )

    def fail_loader(settings, profile):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(
        cli_module,
        "load_catalog_records",
        fail_loader,
    )

    result = runner.invoke(
        app,
        [
            "load-catalog",
            "--profile",
            "smoke",
        ],
    )

    assert result.exit_code == 1
    assert "Catalogue load failed" in result.stdout
    assert "simulated failure" in result.stdout


def test_large_inventory_load_requires_yes() -> None:
    result = runner.invoke(
        app,
        [
            "load-inventory",
            "--profile",
            "large",
        ],
    )

    assert result.exit_code == 2
    assert "Execution blocked" in result.stdout


def test_smoke_inventory_load_executes(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        cli_module,
        "check_database",
        lambda settings: None,
    )

    monkeypatch.setattr(
        cli_module,
        "load_inventory_records",
        lambda settings, profile: InventoryLoadResult(
            warehouses=3,
            stock=100,
            reorder_required=10,
        ),
    )

    result = runner.invoke(
        app,
        [
            "load-inventory",
            "--profile",
            "smoke",
        ],
    )

    assert result.exit_code == 0
    assert "Inventory load completed" in result.stdout
    assert "Stock rows: 100" in result.stdout


def test_foundation_loads_in_dependency_order(
    monkeypatch,
) -> None:
    execution_order: list[str] = []

    monkeypatch.setattr(
        cli_module,
        "check_database",
        lambda settings: execution_order.append("validate"),
    )

    def load_catalog(settings, profile):
        execution_order.append("catalog")

        return CatalogLoadResult(
            brands=5,
            categories=10,
            products=50,
            product_prices=100,
        )

    def load_inventory(settings, profile):
        execution_order.append("inventory")

        return InventoryLoadResult(
            warehouses=3,
            stock=100,
            reorder_required=10,
        )

    def load_identity(settings, profile):
        execution_order.append("identity")

        return IdentityLoadResult(
            customers=20,
            credentials=20,
            addresses=40,
            default_addresses=20,
        )

    monkeypatch.setattr(
        cli_module,
        "load_catalog_records",
        load_catalog,
    )

    monkeypatch.setattr(
        cli_module,
        "load_inventory_records",
        load_inventory,
    )

    monkeypatch.setattr(
        cli_module,
        "load_identity_records",
        load_identity,
    )

    result = runner.invoke(
        app,
        [
            "load-foundation",
            "--profile",
            "smoke",
        ],
    )

    assert result.exit_code == 0

    assert execution_order == [
        "validate",
        "identity",
        "catalog",
        "inventory",
    ]

    assert "Foundation load completed" in result.stdout
    assert "Foundation total: 348" in result.stdout


def test_foundation_stops_when_catalog_fails(
    monkeypatch,
) -> None:
    inventory_called = False

    monkeypatch.setattr(
        cli_module,
        "check_database",
        lambda settings: None,
    )

    def fail_catalog(settings, profile):
        raise RuntimeError("catalogue unavailable")

    def track_inventory(settings, profile):
        nonlocal inventory_called
        inventory_called = True

    monkeypatch.setattr(
        cli_module,
        "load_catalog_records",
        fail_catalog,
    )

    monkeypatch.setattr(
        cli_module,
        "load_identity_records",
        lambda settings, profile: IdentityLoadResult(
            customers=20,
            credentials=20,
            addresses=40,
            default_addresses=20,
        ),
    )

    result = runner.invoke(
        app,
        [
            "load-foundation",
            "--profile",
            "smoke",
        ],
    )

    assert result.exit_code == 1
    assert inventory_called is False
    assert "catalogue unavailable" in result.stdout


def test_large_identity_load_requires_yes() -> None:
    result = runner.invoke(
        app,
        [
            "load-identity",
            "--profile",
            "large",
        ],
    )

    assert result.exit_code == 2
    assert "Execution blocked" in result.stdout


def test_smoke_identity_load_executes(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        cli_module,
        "check_database",
        lambda settings: None,
    )

    monkeypatch.setattr(
        cli_module,
        "load_identity_records",
        lambda settings, profile: IdentityLoadResult(
            customers=20,
            credentials=20,
            addresses=40,
            default_addresses=20,
        ),
    )

    result = runner.invoke(
        app,
        [
            "load-identity",
            "--profile",
            "smoke",
        ],
    )

    assert result.exit_code == 0
    assert "Identity load completed" in result.stdout
    assert "Customers: 20" in result.stdout
    assert "Total identity rows: 80" in result.stdout


def test_load_all_runs_in_dependency_order(
    monkeypatch,
) -> None:
    execution_order: list[str] = []

    monkeypatch.setattr(
        cli_module,
        "check_database",
        lambda settings: execution_order.append("validate"),
    )

    monkeypatch.setattr(
        cli_module,
        "load_identity_records",
        lambda settings, profile: (
            execution_order.append("identity")
            or IdentityLoadResult(
                customers=20,
                credentials=20,
                addresses=40,
                default_addresses=20,
            )
        ),
    )

    monkeypatch.setattr(
        cli_module,
        "load_catalog_records",
        lambda settings, profile: (
            execution_order.append("catalog")
            or CatalogLoadResult(
                brands=5,
                categories=10,
                products=50,
                product_prices=100,
            )
        ),
    )

    monkeypatch.setattr(
        cli_module,
        "load_inventory_records",
        lambda settings, profile: (
            execution_order.append("inventory")
            or InventoryLoadResult(
                warehouses=3,
                stock=100,
                reorder_required=10,
            )
        ),
    )

    monkeypatch.setattr(
        cli_module,
        "load_commerce_records",
        lambda settings, profile: (
            execution_order.append("commerce")
            or CommerceLoadResult(
                carts=102,
                cart_items=306,
                active_carts=2,
            )
        ),
    )

    monkeypatch.setattr(
        cli_module,
        "load_order_records",
        lambda settings, profile: (
            execution_order.append("orders")
            or OrderLoadResult(
                orders=100,
                order_items=300,
                order_addresses=200,
                status_history=300,
            )
        ),
    )

    monkeypatch.setattr(
        cli_module,
        "load_reservation_records",
        lambda settings, profile: (
            execution_order.append("reservations")
            or ReservationLoadResult(
                reservations=270,
                reserved=27,
                consumed=231,
                released=12,
                active_reserved_quantity=73,
                stock_reserved_quantity=73,
            )
        ),
    )

    monkeypatch.setattr(
        cli_module,
        "load_payment_records",
        lambda settings, profile: (
            execution_order.append("payments")
            or PaymentLoadResult(
                payments=100,
                attempts=120,
                status_history=200,
                retry_payments=20,
                total_paid=Decimal("777942.1400"),
                total_refunded=Decimal("39005.4900"),
            )
        ),
    )

    monkeypatch.setattr(
        cli_module,
        "load_event_records",
        lambda settings, profile: (
            execution_order.append("events")
            or EventLoadResult(
                outbox_events=300,
                published_events=290,
                pending_events=10,
                audit_events_attempted=400,
                audit_events_inserted=400,
            )
        ),
    )

    result = runner.invoke(
        app,
        [
            "load-all",
            "--profile",
            "smoke",
        ],
    )

    assert result.exit_code == 0

    assert execution_order == [
        "validate",
        "identity",
        "catalog",
        "inventory",
        "commerce",
        "orders",
        "reservations",
        "payments",
        "events",
    ]

    assert "Complete load finished" in result.stdout
    assert "Complete total: 3,046" in result.stdout


def test_large_complete_load_requires_yes() -> None:
    result = runner.invoke(
        app,
        [
            "load-all",
            "--profile",
            "large",
        ],
    )

    assert result.exit_code == 2
    assert "Execution blocked" in result.stdout
