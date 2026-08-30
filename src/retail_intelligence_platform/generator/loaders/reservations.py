"""Transactional loading for inventory reservations."""

from collections.abc import Iterable
from dataclasses import dataclass

import psycopg

from retail_intelligence_platform.generator.config import (
    GeneratorSettings,
)
from retail_intelligence_platform.generator.domains.reservations import (
    ReservationRecord,
    generate_reservations,
    reservation_count,
)
from retail_intelligence_platform.generator.loaders.catalog import (
    batched,
)
from retail_intelligence_platform.generator.profiles import (
    GenerationProfile,
)


@dataclass(frozen=True, slots=True)
class ReservationLoadResult:
    reservations: int
    reserved: int
    consumed: int
    released: int
    active_reserved_quantity: int
    stock_reserved_quantity: int


def load_reservations(
    settings: GeneratorSettings,
    profile: GenerationProfile,
) -> ReservationLoadResult:
    """Load reservations and reconcile stock atomically."""

    password = settings.load_password()

    with (
        psycopg.connect(
            host=settings.host,
            port=settings.port,
            dbname=settings.database,
            user=settings.user,
            password=password.get_secret_value(),
            connect_timeout=(settings.connect_timeout_seconds),
            application_name=("retail-reservation-loader"),
        ) as connection,
        connection.cursor() as cursor,
    ):
        _load_reservations(
            cursor,
            generate_reservations(profile),
            settings.batch_size,
        )

        _reconcile_reserved_stock(cursor)

        result = _read_generated_counts(cursor)

        _validate_loaded_counts(
            result,
            profile,
        )

        connection.commit()

    return result


def _load_reservations(
    cursor: psycopg.Cursor,
    records: Iterable[ReservationRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO inventory.reservations (
            public_id,
            order_id,
            order_item_id,
            warehouse_id,
            product_id,
            quantity,
            status,
            expires_at,
            created_at,
            updated_at
        )
        SELECT
            %(public_id)s,
            orders.order_id,
            item.order_item_id,
            warehouse.warehouse_id,
            product.product_id,
            %(quantity)s,
            %(status)s,
            %(expires_at)s,
            %(created_at)s,
            %(updated_at)s
        FROM commerce.orders AS orders
        JOIN commerce.order_items AS item
          ON item.order_id = orders.order_id
        JOIN catalog.products AS product
          ON product.product_id = item.product_id
        JOIN inventory.warehouses AS warehouse
          ON warehouse.warehouse_code =
             %(warehouse_code)s
        JOIN inventory.stock AS stock
          ON stock.warehouse_id =
             warehouse.warehouse_id
         AND stock.product_id =
             product.product_id
        WHERE orders.public_id =
                %(order_public_id)s
          AND product.sku =
                %(product_sku)s
        ON CONFLICT (public_id)
        DO UPDATE SET
            quantity = EXCLUDED.quantity,
            status = EXCLUDED.status,
            expires_at = EXCLUDED.expires_at,
            updated_at = EXCLUDED.updated_at,
            version =
                inventory.reservations.version + 1;
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "public_id": record.public_id,
                    "order_public_id": (record.order_public_id),
                    "product_sku": (record.product_sku),
                    "warehouse_code": (record.warehouse_code),
                    "quantity": record.quantity,
                    "status": record.status,
                    "expires_at": (record.expires_at),
                    "created_at": (record.created_at),
                    "updated_at": (record.updated_at),
                }
                for record in batch
            ],
        )


def _reconcile_reserved_stock(
    cursor: psycopg.Cursor,
) -> None:
    """Make stock reservations equal active allocations."""

    cursor.execute(
        """
        WITH desired_quantity AS (
            SELECT
                stock.stock_id,
                COALESCE(
                    sum(reservation.quantity)
                    FILTER (
                        WHERE reservation.status IN (
                            'PENDING',
                            'RESERVED'
                        )
                    ),
                    0
                )::INTEGER AS reserved_quantity
            FROM inventory.stock AS stock
            JOIN inventory.warehouses AS warehouse
              ON warehouse.warehouse_id =
                 stock.warehouse_id
            JOIN catalog.products AS product
              ON product.product_id =
                 stock.product_id
            LEFT JOIN inventory.reservations
                AS reservation
              ON reservation.warehouse_id =
                 stock.warehouse_id
             AND reservation.product_id =
                 stock.product_id
            WHERE warehouse.warehouse_code
                      LIKE 'WH-IN-%'
              AND product.sku LIKE 'SKU-%'
            GROUP BY stock.stock_id
        )
        UPDATE inventory.stock AS stock
        SET
            reserved_quantity =
                desired.reserved_quantity,
            updated_at = clock_timestamp(),
            version = stock.version + 1
        FROM desired_quantity AS desired
        WHERE desired.stock_id = stock.stock_id
          AND stock.reserved_quantity
              IS DISTINCT FROM
              desired.reserved_quantity;
        """
    )


def _read_generated_counts(
    cursor: psycopg.Cursor,
) -> ReservationLoadResult:
    cursor.execute(
        """
        SELECT
            count(*),
            count(*) FILTER (
                WHERE reservation.status =
                    'RESERVED'
            ),
            count(*) FILTER (
                WHERE reservation.status =
                    'CONSUMED'
            ),
            count(*) FILTER (
                WHERE reservation.status =
                    'RELEASED'
            ),
            COALESCE(
                sum(reservation.quantity)
                FILTER (
                    WHERE reservation.status IN (
                        'PENDING',
                        'RESERVED'
                    )
                ),
                0
            )::INTEGER
        FROM inventory.reservations
            AS reservation
        JOIN commerce.orders AS orders
          ON orders.order_id =
             reservation.order_id
        WHERE orders.order_number LIKE
            'ORD-2025-%';
        """
    )

    reservation_row = cursor.fetchone()

    if reservation_row is None:
        raise RuntimeError("Reservation count query returned no result")

    cursor.execute(
        """
        SELECT COALESCE(
            sum(stock.reserved_quantity),
            0
        )::INTEGER
        FROM inventory.stock AS stock
        JOIN inventory.warehouses AS warehouse
          ON warehouse.warehouse_id =
             stock.warehouse_id
        JOIN catalog.products AS product
          ON product.product_id =
             stock.product_id
        WHERE warehouse.warehouse_code
                  LIKE 'WH-IN-%'
          AND product.sku LIKE 'SKU-%';
        """
    )

    stock_row = cursor.fetchone()

    if stock_row is None:
        raise RuntimeError("Stock reservation query returned no result")

    return ReservationLoadResult(
        reservations=reservation_row[0],
        reserved=reservation_row[1],
        consumed=reservation_row[2],
        released=reservation_row[3],
        active_reserved_quantity=(reservation_row[4]),
        stock_reserved_quantity=stock_row[0],
    )


def _validate_loaded_counts(
    result: ReservationLoadResult,
    profile: GenerationProfile,
) -> None:
    expected_reservations = reservation_count(profile)

    errors: list[str] = []

    if result.reservations != expected_reservations:
        errors.append(
            "reservations: expected "
            f"{expected_reservations}, "
            f"found {result.reservations}"
        )

    status_total = result.reserved + result.consumed + result.released

    if status_total != result.reservations:
        errors.append("reservation status counts do not equal total reservations")

    if result.active_reserved_quantity != (result.stock_reserved_quantity):
        errors.append(
            "active reservation quantity "
            f"{result.active_reserved_quantity} "
            "does not match stock reserved quantity "
            f"{result.stock_reserved_quantity}"
        )

    if result.reserved <= 0:
        errors.append("expected at least one active reservation")

    if errors:
        raise RuntimeError("Reservation validation failed:\n- " + "\n- ".join(errors))
