"""Transactional loading for warehouses and stock."""

from collections.abc import Iterable
from dataclasses import dataclass

import psycopg

from retail_intelligence_platform.generator.config import (
    GeneratorSettings,
)
from retail_intelligence_platform.generator.domains.inventory import (
    StockRecord,
    WarehouseRecord,
    generate_stock,
    generate_warehouses,
)
from retail_intelligence_platform.generator.loaders.catalog import (
    batched,
)
from retail_intelligence_platform.generator.profiles import (
    GenerationProfile,
)


@dataclass(frozen=True, slots=True)
class InventoryLoadResult:
    warehouses: int
    stock: int
    reorder_required: int

    @property
    def total_rows(self) -> int:
        return self.warehouses + self.stock


def load_inventory(
    settings: GeneratorSettings,
    profile: GenerationProfile,
) -> InventoryLoadResult:
    """Load warehouses and stock in one transaction."""

    password = settings.load_password()

    with (
        psycopg.connect(
            host=settings.host,
            port=settings.port,
            dbname=settings.database,
            user=settings.user,
            password=password.get_secret_value(),
            connect_timeout=(settings.connect_timeout_seconds),
            application_name="retail-inventory-loader",
        ) as connection,
        connection.cursor() as cursor,
    ):
        _load_warehouses(
            cursor,
            generate_warehouses(profile),
            settings.batch_size,
        )

        _load_stock(
            cursor,
            generate_stock(profile),
            settings.batch_size,
        )

        result = _read_generated_counts(cursor)

        _validate_loaded_counts(
            result,
            profile,
        )

        connection.commit()

    return result


def _load_warehouses(
    cursor: psycopg.Cursor,
    records: Iterable[WarehouseRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO inventory.warehouses (
            public_id,
            warehouse_code,
            warehouse_name,
            address_line_1,
            address_line_2,
            city,
            state_region,
            postal_code,
            country_code,
            is_active
        )
        VALUES (
            %(public_id)s,
            %(warehouse_code)s,
            %(warehouse_name)s,
            %(address_line_1)s,
            %(address_line_2)s,
            %(city)s,
            %(state_region)s,
            %(postal_code)s,
            %(country_code)s,
            %(is_active)s
        )
        ON CONFLICT (warehouse_code)
        DO UPDATE SET
            warehouse_name =
                EXCLUDED.warehouse_name,
            address_line_1 =
                EXCLUDED.address_line_1,
            address_line_2 =
                EXCLUDED.address_line_2,
            city = EXCLUDED.city,
            state_region = EXCLUDED.state_region,
            postal_code = EXCLUDED.postal_code,
            country_code = EXCLUDED.country_code,
            is_active = EXCLUDED.is_active,
            updated_at = clock_timestamp(),
            version =
                inventory.warehouses.version + 1;
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "public_id": record.public_id,
                    "warehouse_code": (record.warehouse_code),
                    "warehouse_name": (record.warehouse_name),
                    "address_line_1": (record.address_line_1),
                    "address_line_2": (record.address_line_2),
                    "city": record.city,
                    "state_region": (record.state_region),
                    "postal_code": (record.postal_code),
                    "country_code": (record.country_code),
                    "is_active": record.is_active,
                }
                for record in batch
            ],
        )


def _load_stock(
    cursor: psycopg.Cursor,
    records: Iterable[StockRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO inventory.stock (
            warehouse_id,
            product_id,
            on_hand_quantity,
            reserved_quantity,
            reorder_level
        )
        SELECT
            warehouse.warehouse_id,
            product.product_id,
            %(on_hand_quantity)s,
            %(reserved_quantity)s,
            %(reorder_level)s
        FROM inventory.warehouses AS warehouse
        CROSS JOIN catalog.products AS product
        WHERE warehouse.warehouse_code =
                %(warehouse_code)s
          AND product.sku = %(product_sku)s
        ON CONFLICT (
            warehouse_id,
            product_id
        )
        DO UPDATE SET
            on_hand_quantity =
                EXCLUDED.on_hand_quantity,
            reserved_quantity =
                EXCLUDED.reserved_quantity,
            reorder_level =
                EXCLUDED.reorder_level,
            updated_at = clock_timestamp(),
            version = inventory.stock.version + 1;
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "warehouse_code": (record.warehouse_code),
                    "product_sku": (record.product_sku),
                    "on_hand_quantity": (record.on_hand_quantity),
                    "reserved_quantity": (record.reserved_quantity),
                    "reorder_level": (record.reorder_level),
                }
                for record in batch
            ],
        )


def _read_generated_counts(
    cursor: psycopg.Cursor,
) -> InventoryLoadResult:
    cursor.execute(
        """
        SELECT
            (
                SELECT count(*)
                FROM inventory.warehouses
                WHERE warehouse_code LIKE
                    'WH-IN-%'
            ),
            (
                SELECT count(*)
                FROM inventory.stock AS stock
                JOIN inventory.warehouses AS warehouse
                  ON warehouse.warehouse_id =
                     stock.warehouse_id
                JOIN catalog.products AS product
                  ON product.product_id =
                     stock.product_id
                WHERE warehouse.warehouse_code
                          LIKE 'WH-IN-%'
                  AND product.sku LIKE 'SKU-%'
            ),
            (
                SELECT count(*)
                FROM inventory.stock AS stock
                JOIN inventory.warehouses AS warehouse
                  ON warehouse.warehouse_id =
                     stock.warehouse_id
                JOIN catalog.products AS product
                  ON product.product_id =
                     stock.product_id
                WHERE warehouse.warehouse_code
                          LIKE 'WH-IN-%'
                  AND product.sku LIKE 'SKU-%'
                  AND stock.available_quantity
                      <= stock.reorder_level
            );
        """
    )

    row = cursor.fetchone()

    if row is None:
        raise RuntimeError("Inventory count query returned no result")

    return InventoryLoadResult(
        warehouses=row[0],
        stock=row[1],
        reorder_required=row[2],
    )


def _validate_loaded_counts(
    result: InventoryLoadResult,
    profile: GenerationProfile,
) -> None:
    expected_warehouses = profile.warehouse_count

    expected_stock = profile.product_count * profile.warehouses_per_product

    errors: list[str] = []

    if result.warehouses != expected_warehouses:
        errors.append(
            f"warehouses: expected {expected_warehouses}, found {result.warehouses}"
        )

    if result.stock != expected_stock:
        errors.append(
            f"stock: expected {expected_stock}, "
            f"found {result.stock}. "
            "Confirm the matching catalogue profile "
            "was loaded first."
        )

    if result.reorder_required <= 0:
        errors.append("expected at least one reorder scenario")

    if errors:
        raise RuntimeError(
            "Inventory row-count validation failed:\n- " + "\n- ".join(errors)
        )
