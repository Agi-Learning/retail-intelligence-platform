"""Transactional loading for immutable order records."""

from collections.abc import Iterable
from dataclasses import dataclass

import psycopg

from retail_intelligence_platform.generator.config import (
    GeneratorSettings,
)
from retail_intelligence_platform.generator.domains.orders import (
    OrderAddressRecord,
    OrderItemRecord,
    OrderRecord,
    OrderStatusHistoryRecord,
    generate_order_addresses,
    generate_order_items,
    generate_order_status_history,
    generate_orders,
)
from retail_intelligence_platform.generator.loaders.catalog import (
    batched,
)
from retail_intelligence_platform.generator.profiles import (
    GenerationProfile,
)


@dataclass(frozen=True, slots=True)
class OrderLoadResult:
    orders: int
    order_items: int
    order_addresses: int
    status_history: int

    @property
    def total_rows(self) -> int:
        return (
            self.orders + self.order_items + self.order_addresses + self.status_history
        )


def load_orders(
    settings: GeneratorSettings,
    profile: GenerationProfile,
) -> OrderLoadResult:
    """Load orders and snapshots in one transaction."""

    password = settings.load_password()

    with (
        psycopg.connect(
            host=settings.host,
            port=settings.port,
            dbname=settings.database,
            user=settings.user,
            password=password.get_secret_value(),
            connect_timeout=(settings.connect_timeout_seconds),
            application_name="retail-order-loader",
        ) as connection,
        connection.cursor() as cursor,
    ):
        _load_orders(
            cursor,
            generate_orders(profile),
            settings.batch_size,
        )

        _load_order_items(
            cursor,
            generate_order_items(profile),
            settings.batch_size,
        )

        _load_order_addresses(
            cursor,
            generate_order_addresses(profile),
            settings.batch_size,
        )

        _load_status_history(
            cursor,
            generate_order_status_history(profile),
            settings.batch_size,
        )

        result = _read_generated_counts(cursor)

        _validate_loaded_counts(
            result,
            profile,
        )

        connection.commit()

    return result


def _load_orders(
    cursor: psycopg.Cursor,
    records: Iterable[OrderRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO commerce.orders (
            public_id,
            order_number,
            customer_id,
            cart_id,
            status,
            currency_code,
            subtotal_amount,
            discount_amount,
            tax_amount,
            shipping_amount,
            total_amount,
            idempotency_key,
            ordered_at,
            created_at,
            updated_at
        )
        SELECT
            %(public_id)s,
            %(order_number)s,
            customer.customer_id,
            cart.cart_id,
            %(status)s,
            %(currency_code)s,
            %(subtotal_amount)s,
            %(discount_amount)s,
            %(tax_amount)s,
            %(shipping_amount)s,
            %(total_amount)s,
            %(idempotency_key)s,
            %(ordered_at)s,
            %(created_at)s,
            %(updated_at)s
        FROM identity.customers AS customer
        CROSS JOIN commerce.carts AS cart
        WHERE customer.email =
                %(customer_email)s
          AND cart.public_id =
                %(cart_public_id)s
        ON CONFLICT (order_number)
        DO NOTHING;
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "public_id": record.public_id,
                    "order_number": (record.order_number),
                    "customer_email": (record.customer_email),
                    "cart_public_id": (record.cart_public_id),
                    "status": record.status,
                    "currency_code": (record.currency_code),
                    "subtotal_amount": (record.subtotal_amount),
                    "discount_amount": (record.discount_amount),
                    "tax_amount": (record.tax_amount),
                    "shipping_amount": (record.shipping_amount),
                    "total_amount": (record.total_amount),
                    "idempotency_key": (record.idempotency_key),
                    "ordered_at": record.ordered_at,
                    "created_at": record.created_at,
                    "updated_at": record.updated_at,
                }
                for record in batch
            ],
        )


def _load_order_items(
    cursor: psycopg.Cursor,
    records: Iterable[OrderItemRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO commerce.order_items (
            order_id,
            product_id,
            sku_snapshot,
            product_name_snapshot,
            quantity,
            unit_price,
            discount_amount,
            tax_amount,
            line_total,
            created_at
        )
        SELECT
            orders.order_id,
            product.product_id,
            %(sku_snapshot)s,
            %(product_name_snapshot)s,
            %(quantity)s,
            %(unit_price)s,
            %(discount_amount)s,
            %(tax_amount)s,
            %(line_total)s,
            %(created_at)s
        FROM commerce.orders AS orders
        CROSS JOIN catalog.products AS product
        WHERE orders.public_id =
                %(order_public_id)s
          AND product.sku =
                %(product_sku)s
        ON CONFLICT (
            order_id,
            product_id
        )
        DO NOTHING;
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "order_public_id": (record.order_public_id),
                    "product_sku": (record.product_sku),
                    "sku_snapshot": (record.sku_snapshot),
                    "product_name_snapshot": (record.product_name_snapshot),
                    "quantity": record.quantity,
                    "unit_price": (record.unit_price),
                    "discount_amount": (record.discount_amount),
                    "tax_amount": (record.tax_amount),
                    "line_total": (record.line_total),
                    "created_at": (record.created_at),
                }
                for record in batch
            ],
        )


def _load_order_addresses(
    cursor: psycopg.Cursor,
    records: Iterable[OrderAddressRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO commerce.order_addresses (
            order_id,
            address_role,
            recipient_name,
            phone_number,
            address_line_1,
            address_line_2,
            city,
            state_region,
            postal_code,
            country_code,
            created_at
        )
        SELECT
            orders.order_id,
            %(address_role)s,
            %(recipient_name)s,
            %(phone_number)s,
            %(address_line_1)s,
            %(address_line_2)s,
            %(city)s,
            %(state_region)s,
            %(postal_code)s,
            %(country_code)s,
            %(created_at)s
        FROM commerce.orders AS orders
        WHERE orders.public_id =
            %(order_public_id)s
        ON CONFLICT (
            order_id,
            address_role
        )
        DO NOTHING;
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "order_public_id": (record.order_public_id),
                    "address_role": (record.address_role),
                    "recipient_name": (record.recipient_name),
                    "phone_number": (record.phone_number),
                    "address_line_1": (record.address_line_1),
                    "address_line_2": (record.address_line_2),
                    "city": record.city,
                    "state_region": (record.state_region),
                    "postal_code": (record.postal_code),
                    "country_code": (record.country_code),
                    "created_at": (record.created_at),
                }
                for record in batch
            ],
        )


def _load_status_history(
    cursor: psycopg.Cursor,
    records: Iterable[OrderStatusHistoryRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO commerce.order_status_history (
            order_id,
            previous_status,
            new_status,
            reason,
            changed_by,
            changed_at
        )
        SELECT
            orders.order_id,
            %(previous_status)s,
            %(new_status)s,
            %(reason)s,
            %(changed_by)s,
            %(changed_at)s
        FROM commerce.orders AS orders
        WHERE orders.public_id =
                %(order_public_id)s
          AND NOT EXISTS (
              SELECT 1
              FROM commerce.order_status_history
                  AS existing
              WHERE existing.order_id =
                      orders.order_id
                AND existing.previous_status
                    IS NOT DISTINCT FROM
                    %(previous_status)s
                AND existing.new_status =
                    %(new_status)s
                AND existing.changed_at =
                    %(changed_at)s
          );
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "order_public_id": (record.order_public_id),
                    "previous_status": (record.previous_status),
                    "new_status": (record.new_status),
                    "reason": record.reason,
                    "changed_by": (record.changed_by),
                    "changed_at": (record.changed_at),
                }
                for record in batch
            ],
        )


def _read_generated_counts(
    cursor: psycopg.Cursor,
) -> OrderLoadResult:
    cursor.execute(
        """
        SELECT
            (
                SELECT count(*)
                FROM commerce.orders
                WHERE order_number LIKE
                    'ORD-2025-%'
            ),
            (
                SELECT count(*)
                FROM commerce.order_items AS item
                JOIN commerce.orders AS orders
                  ON orders.order_id =
                     item.order_id
                WHERE orders.order_number LIKE
                    'ORD-2025-%'
            ),
            (
                SELECT count(*)
                FROM commerce.order_addresses
                    AS address
                JOIN commerce.orders AS orders
                  ON orders.order_id =
                     address.order_id
                WHERE orders.order_number LIKE
                    'ORD-2025-%'
            ),
            (
                SELECT count(*)
                FROM commerce.order_status_history
                    AS history
                JOIN commerce.orders AS orders
                  ON orders.order_id =
                     history.order_id
                WHERE orders.order_number LIKE
                          'ORD-2025-%'
                  AND history.changed_by =
                      'synthetic-generator'
            );
        """
    )

    row = cursor.fetchone()

    if row is None:
        raise RuntimeError("Order count query returned no result")

    return OrderLoadResult(
        orders=row[0],
        order_items=row[1],
        order_addresses=row[2],
        status_history=row[3],
    )


def _validate_loaded_counts(
    result: OrderLoadResult,
    profile: GenerationProfile,
) -> None:
    expected = {
        "orders": profile.order_count,
        "order_items": (profile.order_count * profile.average_items_per_order),
        "order_addresses": (profile.order_count * 2),
        "status_history": (
            profile.order_count * profile.average_status_changes_per_order
        ),
    }

    actual = {
        "orders": result.orders,
        "order_items": result.order_items,
        "order_addresses": (result.order_addresses),
        "status_history": result.status_history,
    }

    errors = [
        f"{name}: expected {expected[name]}, found {actual[name]}"
        for name in expected
        if actual[name] != expected[name]
    ]

    if errors:
        raise RuntimeError(
            "Order row-count validation failed:\n- " + "\n- ".join(errors)
        )
