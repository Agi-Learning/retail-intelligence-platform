"""Deterministic order and order-snapshot generation."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from retail_intelligence_platform.generator.domains.catalog import (
    current_product_list_price,
    product_sku,
)
from retail_intelligence_platform.generator.domains.commerce import (
    generate_carts,
    stable_commerce_uuid,
)
from retail_intelligence_platform.generator.domains.identity import (
    customer_phone,
)
from retail_intelligence_platform.generator.profiles import (
    GenerationProfile,
)

_MONEY_SCALE = Decimal("0.0001")
_TAX_RATE = Decimal("0.1800")
_DISCOUNT_RATE = Decimal("0.0500")
_FREE_SHIPPING_THRESHOLD = Decimal("1000.0000")
_STANDARD_SHIPPING = Decimal("50.0000")

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
class OrderRecord:
    public_id: UUID
    order_number: str
    customer_email: str
    cart_public_id: UUID
    status: str
    currency_code: str
    subtotal_amount: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    shipping_amount: Decimal
    total_amount: Decimal
    idempotency_key: str
    ordered_at: datetime
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class OrderItemRecord:
    order_public_id: UUID
    product_sku: str
    sku_snapshot: str
    product_name_snapshot: str
    quantity: int
    unit_price: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    line_total: Decimal
    created_at: object


@dataclass(frozen=True, slots=True)
class OrderAddressRecord:
    order_public_id: UUID
    address_role: str
    recipient_name: str
    phone_number: str
    address_line_1: str
    address_line_2: str | None
    city: str
    state_region: str
    postal_code: str
    country_code: str
    created_at: object


@dataclass(frozen=True, slots=True)
class OrderStatusHistoryRecord:
    order_public_id: UUID
    previous_status: str | None
    new_status: str
    reason: str
    changed_by: str
    changed_at: object


def order_public_id(order_number: int) -> UUID:
    """Return the deterministic public order UUID."""

    return stable_commerce_uuid(
        "order",
        str(order_number),
    )


def formatted_order_number(order_number: int) -> str:
    """Return a normalized external order number."""

    return f"ORD-2025-{order_number:08d}"


def _final_order_status(order_number: int) -> str:
    if order_number % 20 == 0:
        return "CANCELLED"

    if order_number % 10 == 0:
        return "SHIPPED"

    if order_number % 5 == 0:
        return "PROCESSING"

    return "DELIVERED"


def _item_values(
    profile: GenerationProfile,
    order_number: int,
    item_offset: int,
) -> tuple[int, int, Decimal, Decimal, Decimal, Decimal]:
    product_number = (
        ((order_number - 1) * profile.average_items_per_order + item_offset)
        % profile.product_count
    ) + 1

    quantity = ((order_number + item_offset) % 4) + 1

    unit_price = current_product_list_price(product_number)

    gross_amount = (unit_price * quantity).quantize(_MONEY_SCALE)

    discount_amount = (
        gross_amount * _DISCOUNT_RATE
        if (order_number + item_offset) % 5 == 0
        else Decimal("0.0000")
    ).quantize(_MONEY_SCALE)

    taxable_amount = gross_amount - discount_amount

    tax_amount = (taxable_amount * _TAX_RATE).quantize(_MONEY_SCALE)

    line_total = (gross_amount - discount_amount + tax_amount).quantize(_MONEY_SCALE)

    return (
        product_number,
        quantity,
        unit_price,
        discount_amount,
        tax_amount,
        line_total,
    )


def generate_orders(
    profile: GenerationProfile,
) -> Iterator[OrderRecord]:
    """Yield orders matching historical checked-out carts."""

    historical_carts = (
        cart for cart in generate_carts(profile) if cart.status == "CHECKED_OUT"
    )

    for order_number, cart in enumerate(
        historical_carts,
        start=1,
    ):
        subtotal_amount = Decimal("0.0000")
        discount_amount = Decimal("0.0000")
        tax_amount = Decimal("0.0000")

        for item_offset in range(profile.average_items_per_order):
            (
                _,
                quantity,
                unit_price,
                item_discount,
                item_tax,
                _,
            ) = _item_values(
                profile,
                order_number,
                item_offset,
            )

            subtotal_amount += (unit_price * quantity).quantize(_MONEY_SCALE)

            discount_amount += item_discount
            tax_amount += item_tax

        shipping_amount = (
            Decimal("0.0000")
            if subtotal_amount >= _FREE_SHIPPING_THRESHOLD
            else _STANDARD_SHIPPING
        )

        total_amount = (
            subtotal_amount - discount_amount + tax_amount + shipping_amount
        ).quantize(_MONEY_SCALE)

        ordered_at = cart.created_at + timedelta(minutes=30)

        yield OrderRecord(
            public_id=order_public_id(order_number),
            order_number=formatted_order_number(order_number),
            customer_email=cart.customer_email,
            cart_public_id=cart.public_id,
            status=_final_order_status(order_number),
            currency_code="INR",
            subtotal_amount=(subtotal_amount.quantize(_MONEY_SCALE)),
            discount_amount=(discount_amount.quantize(_MONEY_SCALE)),
            tax_amount=tax_amount.quantize(_MONEY_SCALE),
            shipping_amount=shipping_amount,
            total_amount=total_amount,
            idempotency_key=(f"checkout-{order_number:08d}"),
            ordered_at=ordered_at,
            created_at=ordered_at,
            updated_at=(ordered_at + timedelta(hours=4)),
        )


def generate_order_items(
    profile: GenerationProfile,
) -> Iterator[OrderItemRecord]:
    """Yield immutable product and monetary snapshots."""

    for order_number, order in enumerate(
        generate_orders(profile),
        start=1,
    ):
        for item_offset in range(profile.average_items_per_order):
            (
                product_number,
                quantity,
                unit_price,
                discount_amount,
                tax_amount,
                line_total,
            ) = _item_values(
                profile,
                order_number,
                item_offset,
            )

            sku = product_sku(product_number)

            yield OrderItemRecord(
                order_public_id=order.public_id,
                product_sku=sku,
                sku_snapshot=sku,
                product_name_snapshot=(f"Retail Product {product_number:08d}"),
                quantity=quantity,
                unit_price=unit_price,
                discount_amount=discount_amount,
                tax_amount=tax_amount,
                line_total=line_total,
                created_at=order.created_at,
            )


def generate_order_addresses(
    profile: GenerationProfile,
) -> Iterator[OrderAddressRecord]:
    """Yield billing and shipping address snapshots."""

    for order_number, order in enumerate(
        generate_orders(profile),
        start=1,
    ):
        selected_customer = ((order_number - 1) % profile.customer_count) + 1

        for address_offset, role in enumerate(("BILLING", "SHIPPING")):
            city, state_region, postal_code = _LOCATIONS[
                (order_number + address_offset - 1) % len(_LOCATIONS)
            ]

            yield OrderAddressRecord(
                order_public_id=order.public_id,
                address_role=role,
                recipient_name=(f"Synthetic Customer {selected_customer:09d}"),
                phone_number=customer_phone(selected_customer),
                address_line_1=(
                    f"{selected_customer}, Order Snapshot Block {address_offset + 1}"
                ),
                address_line_2=(None if address_offset == 0 else "Near Central Market"),
                city=city,
                state_region=state_region,
                postal_code=postal_code,
                country_code="IN",
                created_at=order.created_at,
            )


def generate_order_status_history(
    profile: GenerationProfile,
) -> Iterator[OrderStatusHistoryRecord]:
    """Yield an append-only three-step status history."""

    for order in generate_orders(profile):
        statuses = (
            "PENDING",
            "INVENTORY_RESERVED",
            order.status,
        )

        previous_status: str | None = None

        for transition_number, new_status in enumerate(
            statuses,
            start=1,
        ):
            yield OrderStatusHistoryRecord(
                order_public_id=order.public_id,
                previous_status=previous_status,
                new_status=new_status,
                reason=(f"Deterministic lifecycle transition {transition_number}"),
                changed_by="synthetic-generator",
                changed_at=(order.created_at + timedelta(minutes=transition_number)),
            )

            previous_status = new_status
