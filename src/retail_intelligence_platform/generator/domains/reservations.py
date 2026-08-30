"""Deterministic inventory-reservation generation."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from retail_intelligence_platform.generator.domains.inventory import (
    stable_inventory_uuid,
    warehouse_code,
)
from retail_intelligence_platform.generator.domains.orders import (
    final_order_status,
    generate_order_items,
)
from retail_intelligence_platform.generator.profiles import (
    GenerationProfile,
)

_GENERATION_AS_OF = datetime(
    2026,
    8,
    30,
    tzinfo=UTC,
)


@dataclass(frozen=True, slots=True)
class ReservationRecord:
    public_id: UUID
    order_public_id: UUID
    product_sku: str
    warehouse_code: str
    quantity: int
    status: str
    expires_at: datetime
    created_at: datetime
    updated_at: datetime


def reservation_count(
    profile: GenerationProfile,
) -> int:
    """Return the configured reservation-row count."""

    order_item_count = profile.order_count * profile.average_items_per_order

    return int(order_item_count * profile.reservation_ratio)


def _reservation_status(
    order_number: int,
) -> str:
    order_status = final_order_status(order_number)

    if order_status == "CANCELLED":
        return "RELEASED"

    if order_status == "PROCESSING":
        return "RESERVED"

    return "CONSUMED"


def generate_reservations(
    profile: GenerationProfile,
) -> Iterator[ReservationRecord]:
    """Yield reservations for a deterministic item subset."""

    maximum_reservations = reservation_count(profile)

    for reservation_number, item in enumerate(
        generate_order_items(profile),
        start=1,
    ):
        if reservation_number > maximum_reservations:
            break

        order_number = ((reservation_number - 1) // profile.average_items_per_order) + 1

        product_number = int(item.product_sku.removeprefix("SKU-"))

        selected_warehouse = ((product_number - 1) % profile.warehouse_count) + 1

        status = _reservation_status(order_number)

        created_at = item.created_at
        assert isinstance(created_at, datetime)

        if status == "RESERVED":
            expires_at = _GENERATION_AS_OF + timedelta(minutes=15)
            updated_at = _GENERATION_AS_OF
        else:
            expires_at = created_at + timedelta(minutes=15)
            updated_at = created_at + timedelta(minutes=10)

        yield ReservationRecord(
            public_id=stable_inventory_uuid(
                "reservation",
                reservation_number,
            ),
            order_public_id=(item.order_public_id),
            product_sku=item.product_sku,
            warehouse_code=warehouse_code(selected_warehouse),
            quantity=item.quantity,
            status=status,
            expires_at=expires_at,
            created_at=created_at,
            updated_at=updated_at,
        )
