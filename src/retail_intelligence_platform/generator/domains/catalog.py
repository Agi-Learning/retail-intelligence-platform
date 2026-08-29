"""Deterministic catalogue-domain record generation."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from retail_intelligence_platform.generator.profiles import (
    GenerationProfile,
)


_CATALOG_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "retail-intelligence-platform/catalog",
)

_HISTORICAL_PRICE_START = datetime(
    2025,
    1,
    1,
    tzinfo=timezone.utc,
)

_CURRENT_PRICE_START = datetime(
    2026,
    1,
    1,
    tzinfo=timezone.utc,
)


@dataclass(frozen=True, slots=True)
class BrandRecord:
    public_id: UUID
    brand_name: str
    description: str
    website_url: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class CategoryRecord:
    public_id: UUID
    parent_slug: str | None
    category_name: str
    category_slug: str
    description: str
    display_order: int
    is_active: bool


@dataclass(frozen=True, slots=True)
class ProductRecord:
    public_id: UUID
    sku: str
    category_slug: str
    brand_name: str | None
    product_name: str
    product_slug: str
    short_description: str
    full_description: str
    status: str
    attributes: dict[str, Any]
    weight_grams: int


@dataclass(frozen=True, slots=True)
class ProductPriceRecord:
    product_sku: str
    currency_code: str
    list_price: Decimal
    sale_price: Decimal | None
    valid_from: datetime
    valid_to: datetime | None
    created_by: str


def stable_catalog_uuid(
    entity_type: str,
    sequence_number: int,
) -> UUID:
    """Create a reproducible UUID for a catalogue entity."""

    return uuid5(
        _CATALOG_NAMESPACE,
        f"{entity_type}:{sequence_number}",
    )


def brand_name(sequence_number: int) -> str:
    return f"Retail Brand {sequence_number:05d}"


def category_slug(sequence_number: int) -> str:
    return f"category-{sequence_number:05d}"


def product_sku(sequence_number: int) -> str:
    return f"SKU-{sequence_number:08d}"


def generate_brands(
    profile: GenerationProfile,
) -> Iterator[BrandRecord]:
    """Yield deterministic brand records."""

    for sequence_number in range(
        1,
        profile.brand_count + 1,
    ):
        name = brand_name(sequence_number)

        yield BrandRecord(
            public_id=stable_catalog_uuid(
                "brand",
                sequence_number,
            ),
            brand_name=name,
            description=f"Product catalogue for {name}.",
            website_url=(f"https://brand-{sequence_number:05d}.example.com"),
            is_active=sequence_number % 50 != 0,
        )


def generate_categories(
    profile: GenerationProfile,
) -> Iterator[CategoryRecord]:
    """Yield parents before children for safe insertion."""

    root_count = min(10, profile.category_count)

    for sequence_number in range(
        1,
        profile.category_count + 1,
    ):
        parent_slug: str | None = None

        if sequence_number > root_count:
            parent_number = ((sequence_number - root_count - 1) // 5) + 1

            parent_slug = category_slug(parent_number)

        yield CategoryRecord(
            public_id=stable_catalog_uuid(
                "category",
                sequence_number,
            ),
            parent_slug=parent_slug,
            category_name=(f"Retail Category {sequence_number:05d}"),
            category_slug=category_slug(sequence_number),
            description=(f"Deterministic category {sequence_number:05d}."),
            display_order=sequence_number - 1,
            is_active=sequence_number % 100 != 0,
        )


def generate_products(
    profile: GenerationProfile,
) -> Iterator[ProductRecord]:
    """Yield deterministic product-master records."""

    for sequence_number in range(
        1,
        profile.product_count + 1,
    ):
        selected_category = ((sequence_number - 1) % profile.category_count) + 1

        selected_brand = ((sequence_number - 1) % profile.brand_count) + 1

        sku = product_sku(sequence_number)

        yield ProductRecord(
            public_id=stable_catalog_uuid(
                "product",
                sequence_number,
            ),
            sku=sku,
            category_slug=category_slug(selected_category),
            brand_name=(
                None if sequence_number % 10 == 0 else brand_name(selected_brand)
            ),
            product_name=(f"Retail Product {sequence_number:08d}"),
            product_slug=(f"retail-product-{sequence_number:08d}"),
            short_description=(f"Deterministic retail product {sku}."),
            full_description=(
                f"Generated product {sku} for repeatable "
                "data-engineering and analytics workloads."
            ),
            status=("DRAFT" if sequence_number % 20 == 0 else "ACTIVE"),
            attributes={
                "colour": ("blue" if sequence_number % 2 == 0 else "black"),
                "size_code": (sequence_number % 5) + 1,
                "material": ("metal" if sequence_number % 3 == 0 else "composite"),
            },
            weight_grams=100 + (sequence_number % 9_900),
        )


def generate_product_prices(
    profile: GenerationProfile,
) -> Iterator[ProductPriceRecord]:
    """Yield historical and current effective-dated prices."""

    for sequence_number in range(
        1,
        profile.product_count + 1,
    ):
        sku = product_sku(sequence_number)

        base_price = Decimal(100 + ((sequence_number * 37) % 50_000)).quantize(
            Decimal("0.0001")
        )

        historical_price = (base_price * Decimal("1.1000")).quantize(Decimal("0.0001"))

        current_sale_price = (base_price * Decimal("0.9000")).quantize(
            Decimal("0.0001")
        )

        yield ProductPriceRecord(
            product_sku=sku,
            currency_code="INR",
            list_price=historical_price,
            sale_price=None,
            valid_from=_HISTORICAL_PRICE_START,
            valid_to=_CURRENT_PRICE_START,
            created_by="deterministic-generator",
        )

        yield ProductPriceRecord(
            product_sku=sku,
            currency_code="INR",
            list_price=base_price,
            sale_price=(current_sale_price if sequence_number % 4 == 0 else None),
            valid_from=_CURRENT_PRICE_START,
            valid_to=None,
            created_by="deterministic-generator",
        )
