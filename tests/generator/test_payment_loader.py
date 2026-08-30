from decimal import Decimal

import pytest

from retail_intelligence_platform.generator.loaders.payments import (
    PaymentLoadResult,
    _validate_loaded_counts,
)
from retail_intelligence_platform.generator.profiles import (
    get_profile,
)


def valid_result() -> PaymentLoadResult:
    return PaymentLoadResult(
        payments=100,
        attempts=120,
        status_history=200,
        retry_payments=20,
        total_paid=Decimal("100000.0000"),
        total_refunded=Decimal("5000.0000"),
    )


def test_payment_result_total() -> None:
    assert valid_result().total_rows == 420


def test_smoke_payment_counts_are_valid() -> None:
    _validate_loaded_counts(
        valid_result(),
        get_profile("smoke"),
    )


def test_missing_attempts_are_rejected() -> None:
    result = valid_result()

    with pytest.raises(
        RuntimeError,
        match="attempts: expected 120",
    ):
        _validate_loaded_counts(
            PaymentLoadResult(
                payments=result.payments,
                attempts=119,
                status_history=result.status_history,
                retry_payments=19,
                total_paid=result.total_paid,
                total_refunded=(result.total_refunded),
            ),
            get_profile("smoke"),
        )


def test_excessive_refunds_are_rejected() -> None:
    result = valid_result()

    with pytest.raises(
        RuntimeError,
        match="refunded amount exceeds",
    ):
        _validate_loaded_counts(
            PaymentLoadResult(
                payments=result.payments,
                attempts=result.attempts,
                status_history=result.status_history,
                retry_payments=result.retry_payments,
                total_paid=Decimal("100.0000"),
                total_refunded=Decimal("101.0000"),
            ),
            get_profile("smoke"),
        )
