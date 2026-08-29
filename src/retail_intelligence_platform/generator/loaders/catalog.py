"""Transactional PostgreSQL loading for catalogue records."""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import islice

import psycopg
from psycopg.types.json import Jsonb

from retail_intelligence_platform.generator.config import (
    GeneratorSettings,
)
from retail_intelligence_platform.generator.domains.catalog import (
    BrandRecord,
    CategoryRecord,
    ProductPriceRecord,
    ProductRecord,
    generate_brands,
    generate_categories,
    generate_product_prices,
    generate_products,
)
from retail_intelligence_platform.generator.profiles import (
    GenerationProfile,
)


@dataclass(frozen=True, slots=True)
class CatalogLoadResult:
    brands: int
    categories: int
    products: int
    product_prices: int

    @property
    def total_rows(self) -> int:
        return self.brands + self.categories + self.products + self.product_prices


def batched[_Record](
    records: Iterable[_Record],
    batch_size: int,
) -> Iterator[list[_Record]]:
    """Yield bounded lists without materializing all records."""

    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    iterator = iter(records)

    while batch := list(islice(iterator, batch_size)):
        yield batch


def load_catalog(
    settings: GeneratorSettings,
    profile: GenerationProfile,
) -> CatalogLoadResult:
    """Load the deterministic catalogue in one transaction."""

    password = settings.load_password()

    with psycopg.connect(
        host=settings.host,
        port=settings.port,
        dbname=settings.database,
        user=settings.user,
        password=password.get_secret_value(),
        connect_timeout=settings.connect_timeout_seconds,
        application_name="retail-catalog-loader",
    ) as connection:
        with connection.cursor() as cursor:
            _load_brands(
                cursor,
                generate_brands(profile),
                settings.batch_size,
            )

            _load_categories(
                cursor,
                generate_categories(profile),
                settings.batch_size,
            )

            _load_products(
                cursor,
                generate_products(profile),
                settings.batch_size,
            )

            _load_product_prices(
                cursor,
                generate_product_prices(profile),
                settings.batch_size,
            )

            result = _read_generated_counts(cursor)

        connection.commit()

    _validate_loaded_counts(result, profile)

    return result


def _load_brands(
    cursor: psycopg.Cursor,
    records: Iterable[BrandRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO catalog.brands (
            public_id,
            brand_name,
            description,
            website_url,
            is_active
        )
        VALUES (
            %(public_id)s,
            %(brand_name)s,
            %(description)s,
            %(website_url)s,
            %(is_active)s
        )
        ON CONFLICT (brand_name)
        DO UPDATE SET
            description = EXCLUDED.description,
            website_url = EXCLUDED.website_url,
            is_active = EXCLUDED.is_active,
            updated_at = clock_timestamp(),
            version = catalog.brands.version + 1;
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "public_id": record.public_id,
                    "brand_name": record.brand_name,
                    "description": record.description,
                    "website_url": record.website_url,
                    "is_active": record.is_active,
                }
                for record in batch
            ],
        )


def _load_categories(
    cursor: psycopg.Cursor,
    records: Iterable[CategoryRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO catalog.categories (
            public_id,
            parent_category_id,
            category_name,
            category_slug,
            description,
            display_order,
            is_active
        )
        VALUES (
            %(public_id)s,
            (
                SELECT parent.category_id
                FROM catalog.categories AS parent
                WHERE parent.category_slug =
                    %(parent_slug)s
            ),
            %(category_name)s,
            %(category_slug)s,
            %(description)s,
            %(display_order)s,
            %(is_active)s
        )
        ON CONFLICT (category_slug)
        DO UPDATE SET
            parent_category_id =
                EXCLUDED.parent_category_id,
            category_name = EXCLUDED.category_name,
            description = EXCLUDED.description,
            display_order = EXCLUDED.display_order,
            is_active = EXCLUDED.is_active,
            updated_at = clock_timestamp(),
            version = catalog.categories.version + 1;
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "public_id": record.public_id,
                    "parent_slug": record.parent_slug,
                    "category_name": record.category_name,
                    "category_slug": record.category_slug,
                    "description": record.description,
                    "display_order": record.display_order,
                    "is_active": record.is_active,
                }
                for record in batch
            ],
        )


def _load_products(
    cursor: psycopg.Cursor,
    records: Iterable[ProductRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO catalog.products (
            public_id,
            sku,
            category_id,
            brand_id,
            product_name,
            product_slug,
            short_description,
            full_description,
            status,
            attributes,
            weight_grams
        )
        SELECT
            %(public_id)s,
            %(sku)s,
            category.category_id,
            brand.brand_id,
            %(product_name)s,
            %(product_slug)s,
            %(short_description)s,
            %(full_description)s,
            %(status)s,
            %(attributes)s,
            %(weight_grams)s
        FROM catalog.categories AS category
        LEFT JOIN catalog.brands AS brand
          ON brand.brand_name = %(brand_name)s
        WHERE category.category_slug =
            %(category_slug)s
        ON CONFLICT (sku)
        DO UPDATE SET
            category_id = EXCLUDED.category_id,
            brand_id = EXCLUDED.brand_id,
            product_name = EXCLUDED.product_name,
            product_slug = EXCLUDED.product_slug,
            short_description =
                EXCLUDED.short_description,
            full_description =
                EXCLUDED.full_description,
            status = EXCLUDED.status,
            attributes = EXCLUDED.attributes,
            weight_grams = EXCLUDED.weight_grams,
            updated_at = clock_timestamp(),
            version = catalog.products.version + 1;
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "public_id": record.public_id,
                    "sku": record.sku,
                    "category_slug": (record.category_slug),
                    "brand_name": record.brand_name,
                    "product_name": record.product_name,
                    "product_slug": record.product_slug,
                    "short_description": (record.short_description),
                    "full_description": (record.full_description),
                    "status": record.status,
                    "attributes": Jsonb(record.attributes),
                    "weight_grams": record.weight_grams,
                }
                for record in batch
            ],
        )


def _load_product_prices(
    cursor: psycopg.Cursor,
    records: Iterable[ProductPriceRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO catalog.product_prices (
            product_id,
            currency_code,
            list_price,
            sale_price,
            valid_from,
            valid_to,
            created_by
        )
        SELECT
            product.product_id,
            %(currency_code)s,
            %(list_price)s,
            %(sale_price)s,
            %(valid_from)s,
            %(valid_to)s,
            %(created_by)s
        FROM catalog.products AS product
        WHERE product.sku = %(product_sku)s
        ON CONFLICT (
            product_id,
            currency_code,
            valid_from
        )
        DO UPDATE SET
            list_price = EXCLUDED.list_price,
            sale_price = EXCLUDED.sale_price,
            valid_to = EXCLUDED.valid_to,
            created_by = EXCLUDED.created_by;
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "product_sku": record.product_sku,
                    "currency_code": (record.currency_code),
                    "list_price": record.list_price,
                    "sale_price": record.sale_price,
                    "valid_from": record.valid_from,
                    "valid_to": record.valid_to,
                    "created_by": record.created_by,
                }
                for record in batch
            ],
        )


def _read_generated_counts(
    cursor: psycopg.Cursor,
) -> CatalogLoadResult:
    cursor.execute(
        """
        SELECT
            (
                SELECT count(*)
                FROM catalog.brands
                WHERE brand_name LIKE
                    'Retail Brand %'
            ),
            (
                SELECT count(*)
                FROM catalog.categories
                WHERE category_slug LIKE
                    'category-%'
            ),
            (
                SELECT count(*)
                FROM catalog.products
                WHERE sku LIKE 'SKU-%'
            ),
            (
                SELECT count(*)
                FROM catalog.product_prices
                WHERE created_by =
                    'deterministic-generator'
            );
        """
    )

    row = cursor.fetchone()

    if row is None:
        raise RuntimeError("Catalogue count query returned no result")

    return CatalogLoadResult(
        brands=row[0],
        categories=row[1],
        products=row[2],
        product_prices=row[3],
    )


def _validate_loaded_counts(
    result: CatalogLoadResult,
    profile: GenerationProfile,
) -> None:
    expected = {
        "brands": profile.brand_count,
        "categories": profile.category_count,
        "products": profile.product_count,
        "product_prices": (profile.product_count * profile.prices_per_product),
    }

    actual = {
        "brands": result.brands,
        "categories": result.categories,
        "products": result.products,
        "product_prices": result.product_prices,
    }

    errors = [
        f"{name}: expected {expected[name]}, found {actual[name]}"
        for name in expected
        if actual[name] != expected[name]
    ]

    if errors:
        raise RuntimeError(
            "Catalogue row-count validation failed:\n- " + "\n- ".join(errors)
        )
