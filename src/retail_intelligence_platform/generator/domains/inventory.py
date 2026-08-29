"""Deterministic warehouse and stock record generation."""

from collections.abc import Iterator
from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5

from retail_intelligence_platform.generator.domains.catalog import (
    product_sku,
)
from retail_intelligence_platform.generator.profiles import (
    GenerationProfile,
)

_INVENTORY_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "retail-intelligence-platform/inventory",
)

_LOCATIONS = (
    ("Chennai", "Tamil Nadu", "600001"),
    ("Bengaluru", "Karnataka", "560001"),
    ("Hyderabad", "Telangana", "500001"),
    ("Mumbai", "Maharashtra", "400001"),
    ("Delhi", "Delhi", "110001"),
    ("Kolkata", "West Bengal", "700001"),
    ("Pune", "Maharashtra", "411001"),
    ("Ahmedabad", "Gujarat", "380001"),
)


@dataclass(frozen=True, slots=True)
class WarehouseRecord:
    public_id: UUID
    warehouse_code: str
    warehouse_name: str
    address_line_1: str
    address_line_2: str | None
    city: str
    state_region: str
    postal_code: str
    country_code: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class StockRecord:
    warehouse_code: str
    product_sku: str
    on_hand_quantity: int
    reserved_quantity: int
    reorder_level: int

    @property
    def available_quantity(self) -> int:
        return self.on_hand_quantity - self.reserved_quantity

    @property
    def requires_reorder(self) -> bool:
        return self.available_quantity <= self.reorder_level


def stable_inventory_uuid(
    entity_type: str,
    sequence_number: int,
) -> UUID:
    """Create a reproducible UUID for inventory entities."""

    return uuid5(
        _INVENTORY_NAMESPACE,
        f"{entity_type}:{sequence_number}",
    )


def warehouse_code(sequence_number: int) -> str:
    """Return a normalized deterministic warehouse code."""

    return f"WH-IN-{sequence_number:04d}"


def generate_warehouses(
    profile: GenerationProfile,
) -> Iterator[WarehouseRecord]:
    """Yield deterministic Indian warehouse records."""

    for sequence_number in range(
        1,
        profile.warehouse_count + 1,
    ):
        city, state_region, base_postal_code = _LOCATIONS[
            (sequence_number - 1) % len(_LOCATIONS)
        ]

        postal_number = int(base_postal_code) + (
            (sequence_number - 1) // len(_LOCATIONS)
        )

        yield WarehouseRecord(
            public_id=stable_inventory_uuid(
                "warehouse",
                sequence_number,
            ),
            warehouse_code=warehouse_code(sequence_number),
            warehouse_name=(f"{city} Fulfilment Centre {sequence_number:04d}"),
            address_line_1=(f"{sequence_number}, Retail Logistics Park"),
            address_line_2="Industrial Estate",
            city=city,
            state_region=state_region,
            postal_code=f"{postal_number:06d}",
            country_code="IN",
            is_active=sequence_number % 50 != 0,
        )


def generate_stock(
    profile: GenerationProfile,
) -> Iterator[StockRecord]:
    """Yield unique product-to-warehouse stock records."""

    for product_number in range(
        1,
        profile.product_count + 1,
    ):
        for offset in range(profile.warehouses_per_product):
            warehouse_number = (
                (product_number + offset - 1) % profile.warehouse_count
            ) + 1

            on_hand_quantity = 50 + (
                (product_number * 17 + warehouse_number * 13) % 951
            )

            reserved_quantity = (product_number * warehouse_number) % 31

            reserved_quantity = min(
                reserved_quantity,
                on_hand_quantity,
            )

            available_quantity = on_hand_quantity - reserved_quantity

            if (product_number + warehouse_number) % 10 == 0:
                reorder_level = available_quantity + 10
            else:
                reorder_level = available_quantity // 5

            yield StockRecord(
                warehouse_code=warehouse_code(warehouse_number),
                product_sku=product_sku(product_number),
                on_hand_quantity=on_hand_quantity,
                reserved_quantity=reserved_quantity,
                reorder_level=reorder_level,
            )
