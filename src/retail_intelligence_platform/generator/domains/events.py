"""Deterministic Outbox and audit-event generation."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from retail_intelligence_platform.generator.domains.orders import (
    generate_orders,
)
from retail_intelligence_platform.generator.profiles import (
    GenerationProfile,
)

_EVENT_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "retail-intelligence-platform/events",
)


@dataclass(frozen=True, slots=True)
class OutboxEventRecord:
    event_id: UUID
    aggregate_type: str
    aggregate_id: str
    event_type: str
    event_version: int
    payload: dict[str, Any]
    headers: dict[str, Any]
    status: str
    occurred_at: datetime
    created_at: datetime
    published_at: datetime | None
    retry_count: int
    last_error: str | None


@dataclass(frozen=True, slots=True)
class AuditEventRecord:
    event_key: UUID
    actor_type: str
    actor_id: str | None
    action: str
    entity_type: str
    entity_id: str
    source_ip: str | None
    correlation_id: UUID | None
    details: dict[str, Any]
    occurred_at: datetime


def event_uuid(
    event_type: str,
    order_number: int,
) -> UUID:
    """Return a deterministic event identifier."""

    return uuid5(
        _EVENT_NAMESPACE,
        f"{event_type}:{order_number}",
    )


def stable_audit_event_key(
    order_public_id: UUID,
    action: str,
) -> UUID:
    """Return a stable idempotency key for one generated audit event."""

    return uuid5(
        _EVENT_NAMESPACE,
        f"audit:{order_public_id}:{action}",
    )


def _correlation_id(order_number: int) -> UUID:
    return uuid5(
        _EVENT_NAMESPACE,
        f"correlation:{order_number}",
    )


def generate_outbox_events(
    profile: GenerationProfile,
) -> Iterator[OutboxEventRecord]:
    """Yield three domain events per order."""

    event_types = (
        "OrderCreated",
        "InventoryReservationUpdated",
        "PaymentFinalized",
    )

    for order_number, order in enumerate(
        generate_orders(profile),
        start=1,
    ):
        correlation_id = _correlation_id(order_number)

        for event_offset, event_type in enumerate(
            event_types,
            start=1,
        ):
            occurred_at = order.created_at + timedelta(minutes=event_offset)

            is_pending = order_number % 10 == 0 and event_offset == 3

            status = "PENDING" if is_pending else "PUBLISHED"

            yield OutboxEventRecord(
                event_id=event_uuid(
                    event_type,
                    order_number,
                ),
                aggregate_type="Order",
                aggregate_id=str(order.public_id),
                event_type=event_type,
                event_version=1,
                payload={
                    "order_id": str(order.public_id),
                    "order_number": (order.order_number),
                    "customer_email": (order.customer_email),
                    "currency_code": (order.currency_code),
                    "total_amount": str(order.total_amount),
                    "order_status": order.status,
                },
                headers={
                    "correlation_id": str(correlation_id),
                    "event_source": ("synthetic-generator"),
                    "content_type": ("application/json"),
                },
                status=status,
                occurred_at=occurred_at,
                created_at=occurred_at,
                published_at=(
                    None if is_pending else occurred_at + timedelta(seconds=30)
                ),
                retry_count=0,
                last_error=None,
            )


def generate_audit_events(
    profile: GenerationProfile,
) -> Iterator[AuditEventRecord]:
    """Yield four non-secret audit events per order."""

    audit_definitions = (
        (
            "CUSTOMER",
            "ORDER_CREATED",
            "ORDER",
        ),
        (
            "SERVICE",
            "INVENTORY_RESERVED",
            "INVENTORY_RESERVATION",
        ),
        (
            "SERVICE",
            "PAYMENT_PROCESSED",
            "PAYMENT",
        ),
        (
            "SYSTEM",
            "ORDER_STATUS_CHANGED",
            "ORDER",
        ),
    )

    for order_number, order in enumerate(
        generate_orders(profile),
        start=1,
    ):
        correlation_id = _correlation_id(order_number)

        source_ip = f"198.51.100.{((order_number - 1) % 254) + 1}"

        for event_offset, (
            actor_type,
            action,
            entity_type,
        ) in enumerate(
            audit_definitions,
            start=1,
        ):
            actor_id = (
                order.customer_email
                if actor_type == "CUSTOMER"
                else "synthetic-generator"
            )
            occurred_at = order.created_at + timedelta(minutes=event_offset)

            yield AuditEventRecord(
                event_key=stable_audit_event_key(
                    order.public_id,
                    "ORDER_CREATED",
                ),
                actor_type="CUSTOMER",
                actor_id=order.customer_email,
                action="ORDER_CREATED",
                entity_type="ORDER",
                entity_id=str(order.public_id),
                source_ip=source_ip,
                correlation_id=correlation_id,
                details={
                    "order_number": order.order_number,
                    "order_status": order.status,
                    "event_source": "synthetic-generator",
                },
                occurred_at=occurred_at,
            )
