"""Deterministic source-data generation profiles."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final


@dataclass(frozen=True, slots=True)
class GenerationProfile:
    """Scale and distribution settings for one generation run."""

    name: str
    seed: int

    customer_count: int
    brand_count: int
    category_count: int
    product_count: int
    warehouse_count: int
    order_count: int

    addresses_per_customer: int = 2
    prices_per_product: int = 2
    warehouses_per_product: int = 3
    active_cart_ratio: float = 0.10
    average_items_per_cart: int = 3
    average_items_per_order: int = 3
    average_status_changes_per_order: int = 3
    payment_attempts_per_order: float = 1.20
    reservation_ratio: float = 0.90
    outbox_events_per_order: int = 3
    audit_events_per_order: int = 4

    def __post_init__(self) -> None:
        integer_fields = (
            "seed",
            "customer_count",
            "brand_count",
            "category_count",
            "product_count",
            "warehouse_count",
            "order_count",
            "addresses_per_customer",
            "prices_per_product",
            "warehouses_per_product",
            "average_items_per_cart",
            "average_items_per_order",
            "average_status_changes_per_order",
            "outbox_events_per_order",
            "audit_events_per_order",
        )

        for field_name in integer_fields:
            value = getattr(self, field_name)

            if value < 0:
                raise ValueError(f"{field_name} must be nonnegative, received {value}")

        ratio_fields = (
            "active_cart_ratio",
            "reservation_ratio",
        )

        for field_name in ratio_fields:
            value = getattr(self, field_name)

            if not 0 <= value <= 1:
                raise ValueError(
                    f"{field_name} must be between 0 and 1, received {value}"
                )

        if self.payment_attempts_per_order < 1:
            raise ValueError("payment_attempts_per_order must be at least 1")

        if self.warehouses_per_product > self.warehouse_count:
            raise ValueError("warehouses_per_product cannot exceed warehouse_count")

    @property
    def estimated_rows(self) -> Mapping[str, int]:
        """Estimate generated rows per table."""

        active_cart_count = int(self.customer_count * self.active_cart_ratio)

        historical_cart_count = self.order_count
        cart_count = historical_cart_count + active_cart_count

        order_item_count = self.order_count * self.average_items_per_order

        return MappingProxyType(
            {
                "identity.customers": self.customer_count,
                "identity.credentials": self.customer_count,
                "identity.addresses": (
                    self.customer_count * self.addresses_per_customer
                ),
                "catalog.brands": self.brand_count,
                "catalog.categories": self.category_count,
                "catalog.products": self.product_count,
                "catalog.product_prices": (
                    self.product_count * self.prices_per_product
                ),
                "inventory.warehouses": self.warehouse_count,
                "inventory.stock": (self.product_count * self.warehouses_per_product),
                "commerce.carts": cart_count,
                "commerce.cart_items": (cart_count * self.average_items_per_cart),
                "commerce.orders": self.order_count,
                "commerce.order_items": order_item_count,
                "commerce.order_addresses": (self.order_count * 2),
                "commerce.order_status_history": (
                    self.order_count * self.average_status_changes_per_order
                ),
                "inventory.reservations": int(
                    order_item_count * self.reservation_ratio
                ),
                "payment.payments": self.order_count,
                "payment.payment_attempts": int(
                    self.order_count * self.payment_attempts_per_order
                ),
                "payment.payment_status_history": (self.order_count * 2),
                "outbox.events": (self.order_count * self.outbox_events_per_order),
                "audit.audit_events": (self.order_count * self.audit_events_per_order),
            }
        )

    @property
    def estimated_total_rows(self) -> int:
        """Estimate total rows generated across all business tables."""

        return sum(self.estimated_rows.values())


_PROFILES: Final[Mapping[str, GenerationProfile]] = MappingProxyType(
    {
        "smoke": GenerationProfile(
            name="smoke",
            seed=20260829,
            customer_count=20,
            brand_count=5,
            category_count=10,
            product_count=50,
            warehouse_count=3,
            order_count=100,
            warehouses_per_product=2,
        ),
        "small": GenerationProfile(
            name="small",
            seed=20260829,
            customer_count=10_000,
            brand_count=100,
            category_count=250,
            product_count=5_000,
            warehouse_count=10,
            order_count=50_000,
        ),
        "medium": GenerationProfile(
            name="medium",
            seed=20260829,
            customer_count=250_000,
            brand_count=500,
            category_count=1_000,
            product_count=50_000,
            warehouse_count=25,
            order_count=2_000_000,
        ),
        "large": GenerationProfile(
            name="large",
            seed=20260829,
            customer_count=1_000_000,
            brand_count=1_000,
            category_count=2_500,
            product_count=200_000,
            warehouse_count=50,
            order_count=10_000_000,
        ),
        "stress": GenerationProfile(
            name="stress",
            seed=20260829,
            customer_count=5_000_000,
            brand_count=2_000,
            category_count=5_000,
            product_count=500_000,
            warehouse_count=100,
            order_count=25_000_000,
        ),
    }
)


def available_profiles() -> tuple[str, ...]:
    """Return supported profile names in configured order."""

    return tuple(_PROFILES)


def get_profile(name: str) -> GenerationProfile:
    """Return one profile or raise a helpful validation error."""

    normalized_name = name.strip().lower()

    try:
        return _PROFILES[normalized_name]
    except KeyError as error:
        supported = ", ".join(available_profiles())
        raise ValueError(
            f"Unknown profile {name!r}. Supported profiles: {supported}"
        ) from error
