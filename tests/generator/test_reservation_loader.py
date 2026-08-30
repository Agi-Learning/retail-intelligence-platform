import pytest

from retail_intelligence_platform.generator.loaders.reservations import (
    ReservationLoadResult,
    _validate_loaded_counts,
)
from retail_intelligence_platform.generator.profiles import (
    get_profile,
)


def valid_result() -> ReservationLoadResult:
    return ReservationLoadResult(
        reservations=270,
        reserved=27,
        consumed=231,
        released=12,
        active_reserved_quantity=70,
        stock_reserved_quantity=70,
    )


def test_smoke_reservation_counts_are_valid() -> None:
    _validate_loaded_counts(
        valid_result(),
        get_profile("smoke"),
    )


def test_missing_reservations_are_rejected() -> None:
    result = valid_result()

    with pytest.raises(
        RuntimeError,
        match="reservations: expected 270",
    ):
        _validate_loaded_counts(
            ReservationLoadResult(
                reservations=269,
                reserved=result.reserved,
                consumed=230,
                released=result.released,
                active_reserved_quantity=70,
                stock_reserved_quantity=70,
            ),
            get_profile("smoke"),
        )


def test_stock_mismatch_is_rejected() -> None:
    result = valid_result()

    with pytest.raises(
        RuntimeError,
        match="does not match",
    ):
        _validate_loaded_counts(
            ReservationLoadResult(
                reservations=result.reservations,
                reserved=result.reserved,
                consumed=result.consumed,
                released=result.released,
                active_reserved_quantity=70,
                stock_reserved_quantity=69,
            ),
            get_profile("smoke"),
        )


def test_missing_active_reservations_are_rejected() -> None:
    with pytest.raises(
        RuntimeError,
        match="active reservation",
    ):
        _validate_loaded_counts(
            ReservationLoadResult(
                reservations=270,
                reserved=0,
                consumed=258,
                released=12,
                active_reserved_quantity=0,
                stock_reserved_quantity=0,
            ),
            get_profile("smoke"),
        )
