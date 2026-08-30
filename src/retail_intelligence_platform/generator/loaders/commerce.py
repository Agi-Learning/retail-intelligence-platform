"""Transactional loading for shopping carts."""

from collections.abc import Iterable
from dataclasses import dataclass

import psycopg

from retail_intelligence_platform.generator.config import (
    GeneratorSettings,
)
from retail_intelligence_platform.generator.domains.commerce import (
    CartItemRecord,
    CartRecord,
    active_cart_count,
    generate_cart_items,
    generate_carts,
)
from retail_intelligence_platform.generator.loaders.catalog import (
    batched,
)
from retail_intelligence_platform.generator.profiles import (
    GenerationProfile,
)


@dataclass(frozen=True, slots=True)
class CommerceLoadResult:
    carts: int
    cart_items: int
    active_carts: int

    @property
    def total_rows(self) -> int:
        return self.carts + self.cart_items


def load_commerce(
    settings: GeneratorSettings,
    profile: GenerationProfile,
) -> CommerceLoadResult:
    """Load carts and items in one transaction."""

    password = settings.load_password()

    with (
        psycopg.connect(
            host=settings.host,
            port=settings.port,
            dbname=settings.database,
            user=settings.user,
            password=password.get_secret_value(),
            connect_timeout=(settings.connect_timeout_seconds),
            application_name="retail-commerce-loader",
        ) as connection,
        connection.cursor() as cursor,
    ):
        _load_carts(
            cursor,
            generate_carts(profile),
            settings.batch_size,
        )

        _load_cart_items(
            cursor,
            generate_cart_items(profile),
            settings.batch_size,
        )

        result = _read_generated_counts(cursor)

        _validate_loaded_counts(
            result,
            profile,
        )

        connection.commit()

    return result


def _load_carts(
    cursor: psycopg.Cursor,
    records: Iterable[CartRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO commerce.carts (
            public_id,
            customer_id,
            status,
            currency_code,
            created_at,
            updated_at,
            expires_at
        )
        SELECT
            %(public_id)s,
            customer.customer_id,
            %(status)s,
            %(currency_code)s,
            %(created_at)s,
            %(updated_at)s,
            %(expires_at)s
        FROM identity.customers AS customer
        WHERE customer.email = %(customer_email)s
        ON CONFLICT (public_id)
        DO UPDATE SET
            customer_id = EXCLUDED.customer_id,
            status = EXCLUDED.status,
            currency_code = EXCLUDED.currency_code,
            updated_at = EXCLUDED.updated_at,
            expires_at = EXCLUDED.expires_at,
            version = commerce.carts.version + 1;
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "public_id": record.public_id,
                    "customer_email": (record.customer_email),
                    "status": record.status,
                    "currency_code": (record.currency_code),
                    "created_at": record.created_at,
                    "updated_at": record.updated_at,
                    "expires_at": record.expires_at,
                }
                for record in batch
            ],
        )


def _load_cart_items(
    cursor: psycopg.Cursor,
    records: Iterable[CartItemRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO commerce.cart_items (
            cart_id,
            product_id,
            quantity,
            displayed_unit_price,
            added_at,
            updated_at
        )
        SELECT
            cart.cart_id,
            product.product_id,
            %(quantity)s,
            %(displayed_unit_price)s,
            %(added_at)s,
            %(updated_at)s
        FROM commerce.carts AS cart
        CROSS JOIN catalog.products AS product
        WHERE cart.public_id = %(cart_public_id)s
          AND product.sku = %(product_sku)s
        ON CONFLICT (
            cart_id,
            product_id
        )
        DO UPDATE SET
            quantity = EXCLUDED.quantity,
            displayed_unit_price =
                EXCLUDED.displayed_unit_price,
            updated_at = EXCLUDED.updated_at,
            version =
                commerce.cart_items.version + 1;
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "cart_public_id": (record.cart_public_id),
                    "product_sku": (record.product_sku),
                    "quantity": record.quantity,
                    "displayed_unit_price": (record.displayed_unit_price),
                    "added_at": record.added_at,
                    "updated_at": record.updated_at,
                }
                for record in batch
            ],
        )


def _read_generated_counts(
    cursor: psycopg.Cursor,
) -> CommerceLoadResult:
    cursor.execute(
        """
        SELECT
            (
                SELECT count(*)
                FROM commerce.carts AS cart
                JOIN identity.customers AS customer
                  ON customer.customer_id =
                     cart.customer_id
                WHERE customer.email LIKE
                    'customer-%@example.test'
            ),
            (
                SELECT count(*)
                FROM commerce.cart_items AS item
                JOIN commerce.carts AS cart
                  ON cart.cart_id = item.cart_id
                JOIN identity.customers AS customer
                  ON customer.customer_id =
                     cart.customer_id
                JOIN catalog.products AS product
                  ON product.product_id =
                     item.product_id
                WHERE customer.email LIKE
                          'customer-%@example.test'
                  AND product.sku LIKE 'SKU-%'
            ),
            (
                SELECT count(*)
                FROM commerce.carts AS cart
                JOIN identity.customers AS customer
                  ON customer.customer_id =
                     cart.customer_id
                WHERE customer.email LIKE
                          'customer-%@example.test'
                  AND cart.status = 'ACTIVE'
            );
        """
    )

    row = cursor.fetchone()

    if row is None:
        raise RuntimeError("Commerce count query returned no result")

    return CommerceLoadResult(
        carts=row[0],
        cart_items=row[1],
        active_carts=row[2],
    )


def _validate_loaded_counts(
    result: CommerceLoadResult,
    profile: GenerationProfile,
) -> None:
    expected = {
        "carts": (profile.order_count + active_cart_count(profile)),
        "cart_items": (
            (profile.order_count + active_cart_count(profile))
            * profile.average_items_per_cart
        ),
        "active_carts": active_cart_count(profile),
    }

    actual = {
        "carts": result.carts,
        "cart_items": result.cart_items,
        "active_carts": result.active_carts,
    }

    errors = [
        f"{name}: expected {expected[name]}, found {actual[name]}"
        for name in expected
        if actual[name] != expected[name]
    ]

    if errors:
        raise RuntimeError(
            "Commerce row-count validation failed:\n- " + "\n- ".join(errors)
        )
