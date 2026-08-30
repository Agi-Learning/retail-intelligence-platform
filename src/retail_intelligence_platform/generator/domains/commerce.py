"""Deterministic shopping-cart record generation."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from retail_intelligence_platform.generator.domains.catalog import (
    current_product_list_price,
    product_sku,
)
from retail_intelligence_platform.generator.domains.identity import (
    customer_email,
)
from retail_intelligence_platform.generator.profiles import (
    GenerationProfile,
)

_COMMERCE_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "retail-intelligence-platform/commerce",
)

_HISTORICAL_CART_START = datetime(
    2025,
    1,
    1,
    tzinfo=UTC,
)

_ACTIVE_CART_START = datetime(
    2026,
    8,
    1,
    tzinfo=UTC,
)


@dataclass(frozen=True, slots=True)
class CartRecord:
    public_id: UUID
    customer_email: str
    status: str
    currency_code: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class CartItemRecord:
    cart_public_id: UUID
    product_sku: str
    quantity: int
    displayed_unit_price: Decimal
    added_at: datetime
    updated_at: datetime


def stable_commerce_uuid(
    entity_type: str,
    sequence_key: str,
) -> UUID:
    """Create a reproducible commerce UUID."""

    return uuid5(
        _COMMERCE_NAMESPACE,
        f"{entity_type}:{sequence_key}",
    )


def active_cart_count(
    profile: GenerationProfile,
) -> int:
    """Return the configured number of active carts."""

    return int(profile.customer_count * profile.active_cart_ratio)


def generate_carts(
    profile: GenerationProfile,
) -> Iterator[CartRecord]:
    """Yield historical carts followed by active carts."""

    for order_number in range(
        1,
        profile.order_count + 1,
    ):
        created_at = _HISTORICAL_CART_START + timedelta(minutes=order_number)

        selected_customer = ((order_number - 1) % profile.customer_count) + 1

        yield CartRecord(
            public_id=stable_commerce_uuid(
                "cart",
                f"historical:{order_number}",
            ),
            customer_email=customer_email(selected_customer),
            status="CHECKED_OUT",
            currency_code="INR",
            created_at=created_at,
            updated_at=(created_at + timedelta(minutes=30)),
            expires_at=None,
        )

    for active_number in range(
        1,
        active_cart_count(profile) + 1,
    ):
        created_at = _ACTIVE_CART_START + timedelta(minutes=active_number)

        yield CartRecord(
            public_id=stable_commerce_uuid(
                "cart",
                f"active:{active_number}",
            ),
            customer_email=customer_email(active_number),
            status="ACTIVE",
            currency_code="INR",
            created_at=created_at,
            updated_at=created_at,
            expires_at=(created_at + timedelta(days=30)),
        )


def generate_cart_items(
    profile: GenerationProfile,
) -> Iterator[CartItemRecord]:
    """Yield unique deterministic products for each cart."""

    for cart_number, cart in enumerate(
        generate_carts(profile),
        start=1,
    ):
        for item_offset in range(profile.average_items_per_cart):
            product_number = (
                ((cart_number - 1) * profile.average_items_per_cart + item_offset)
                % profile.product_count
            ) + 1

            added_at = cart.created_at + timedelta(seconds=item_offset)

            yield CartItemRecord(
                cart_public_id=cart.public_id,
                product_sku=product_sku(product_number),
                quantity=((cart_number + item_offset) % 4) + 1,
                displayed_unit_price=(current_product_list_price(product_number)),
                added_at=added_at,
                updated_at=added_at,
            )
