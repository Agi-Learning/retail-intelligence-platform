"""Deterministic payment-domain record generation."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from retail_intelligence_platform.generator.domains.orders import (
    OrderRecord,
    generate_orders,
)
from retail_intelligence_platform.generator.profiles import (
    GenerationProfile,
)

_PAYMENT_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "retail-intelligence-platform/payment",
)

_MONEY_SCALE = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class PaymentRecord:
    public_id: UUID
    order_public_id: UUID
    status: str
    currency_code: str
    requested_amount: Decimal
    paid_amount: Decimal
    refunded_amount: Decimal
    payment_method: str
    provider_name: str
    provider_payment_reference: str | None
    idempotency_key: str
    initiated_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PaymentAttemptRecord:
    payment_public_id: UUID
    attempt_number: int
    status: str
    provider_request_id: str
    provider_response_code: str | None
    failure_reason: str | None
    requested_at: datetime
    responded_at: datetime | None


@dataclass(frozen=True, slots=True)
class PaymentStatusHistoryRecord:
    payment_public_id: UUID
    previous_status: str | None
    new_status: str
    reason: str
    changed_at: datetime


def payment_public_id(
    payment_number: int,
) -> UUID:
    """Return a deterministic payment UUID."""

    return uuid5(
        _PAYMENT_NAMESPACE,
        f"payment:{payment_number}",
    )


def _payment_status(
    order: OrderRecord,
    payment_number: int,
) -> str:
    if order.status == "CANCELLED":
        return "CANCELLED"

    if order.status == "PROCESSING":
        return "PROCESSING"

    if payment_number % 29 == 0:
        return "REFUNDED"

    if payment_number % 17 == 0:
        return "PARTIALLY_REFUNDED"

    return "SUCCEEDED"


def _payment_amounts(
    status: str,
    requested_amount: Decimal,
) -> tuple[Decimal, Decimal]:
    if status in {
        "CANCELLED",
        "PROCESSING",
        "FAILED",
    }:
        return (
            Decimal("0.0000"),
            Decimal("0.0000"),
        )

    paid_amount = requested_amount

    if status == "REFUNDED":
        refunded_amount = paid_amount
    elif status == "PARTIALLY_REFUNDED":
        refunded_amount = (paid_amount / Decimal(2)).quantize(_MONEY_SCALE)
    else:
        refunded_amount = Decimal("0.0000")

    return paid_amount, refunded_amount


def generate_payments(
    profile: GenerationProfile,
) -> Iterator[PaymentRecord]:
    """Yield one logical payment per order."""

    for payment_number, order in enumerate(
        generate_orders(profile),
        start=1,
    ):
        status = _payment_status(
            order,
            payment_number,
        )

        requested_amount = (order.total_amount).quantize(_MONEY_SCALE)

        paid_amount, refunded_amount = _payment_amounts(
            status,
            requested_amount,
        )

        initiated_at = order.created_at + timedelta(minutes=5)

        completed_at = (
            None if status == "PROCESSING" else initiated_at + timedelta(minutes=2)
        )

        yield PaymentRecord(
            public_id=payment_public_id(payment_number),
            order_public_id=order.public_id,
            status=status,
            currency_code=order.currency_code,
            requested_amount=requested_amount,
            paid_amount=paid_amount,
            refunded_amount=refunded_amount,
            payment_method=("UPI" if payment_number % 2 == 0 else "CARD"),
            provider_name="SyntheticPay",
            provider_payment_reference=(
                None
                if status
                in {
                    "CANCELLED",
                    "PROCESSING",
                }
                else f"pay-{payment_number:010d}"
            ),
            idempotency_key=(f"payment-{payment_number:010d}"),
            initiated_at=initiated_at,
            completed_at=completed_at,
            created_at=initiated_at,
            updated_at=(completed_at or initiated_at),
        )


def payment_attempt_count(
    profile: GenerationProfile,
) -> int:
    """Return the target provider-attempt count."""

    return round(profile.order_count * profile.payment_attempts_per_order)


def generate_payment_attempts(
    profile: GenerationProfile,
) -> Iterator[PaymentAttemptRecord]:
    """Yield first attempts and deterministic retries."""

    extra_attempts = payment_attempt_count(profile) - profile.order_count

    for payment_number, payment in enumerate(
        generate_payments(profile),
        start=1,
    ):
        has_retry = payment_number <= extra_attempts

        first_status = "FAILED" if has_retry else _authorization_status(payment.status)

        first_requested_at = payment.initiated_at

        yield PaymentAttemptRecord(
            payment_public_id=payment.public_id,
            attempt_number=1,
            status=first_status,
            provider_request_id=(f"req-{payment_number:010d}-01"),
            provider_response_code=(
                "DECLINED" if has_retry else _response_code(first_status)
            ),
            failure_reason=("Synthetic provider decline" if has_retry else None),
            requested_at=first_requested_at,
            responded_at=(
                None
                if first_status == "PROCESSING"
                else first_requested_at + timedelta(seconds=30)
            ),
        )

        if has_retry:
            retry_status = _authorization_status(payment.status)

            retry_requested_at = first_requested_at + timedelta(minutes=1)

            yield PaymentAttemptRecord(
                payment_public_id=(payment.public_id),
                attempt_number=2,
                status=retry_status,
                provider_request_id=(f"req-{payment_number:010d}-02"),
                provider_response_code=(_response_code(retry_status)),
                failure_reason=None,
                requested_at=retry_requested_at,
                responded_at=(
                    None
                    if retry_status == "PROCESSING"
                    else retry_requested_at + timedelta(seconds=30)
                ),
            )


def _authorization_status(
    payment_status: str,
) -> str:
    if payment_status in {
        "REFUNDED",
        "PARTIALLY_REFUNDED",
    }:
        return "SUCCEEDED"

    return payment_status


def _response_code(
    attempt_status: str,
) -> str | None:
    if attempt_status == "PROCESSING":
        return None

    if attempt_status == "SUCCEEDED":
        return "APPROVED"

    if attempt_status == "CANCELLED":
        return "CANCELLED"

    return "FAILED"


def generate_payment_status_history(
    profile: GenerationProfile,
) -> Iterator[PaymentStatusHistoryRecord]:
    """Yield initial and final payment states."""

    for payment in generate_payments(profile):
        yield PaymentStatusHistoryRecord(
            payment_public_id=payment.public_id,
            previous_status=None,
            new_status="INITIATED",
            reason="Payment initiated",
            changed_at=payment.initiated_at,
        )

        yield PaymentStatusHistoryRecord(
            payment_public_id=payment.public_id,
            previous_status="INITIATED",
            new_status=payment.status,
            reason="Deterministic final state",
            changed_at=(
                payment.completed_at or payment.initiated_at + timedelta(minutes=1)
            ),
        )
