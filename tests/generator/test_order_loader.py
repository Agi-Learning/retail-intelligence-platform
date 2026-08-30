import pytest

from retail_intelligence_platform.generator.loaders.orders import (
    OrderLoadResult,
    _validate_loaded_counts,
)
from retail_intelligence_platform.generator.profiles import (
    get_profile,
)


def test_order_result_total() -> None:
    result = OrderLoadResult(
        orders=100,
        order_items=300,
        order_addresses=200,
        status_history=300,
    )

    assert result.total_rows == 900


def test_smoke_order_counts_are_valid() -> None:
    _validate_loaded_counts(
        OrderLoadResult(
            orders=100,
            order_items=300,
            order_addresses=200,
            status_history=300,
        ),
        get_profile("smoke"),
    )


def test_missing_items_are_rejected() -> None:
    with pytest.raises(
        RuntimeError,
        match="order_items: expected 300",
    ):
        _validate_loaded_counts(
            OrderLoadResult(
                orders=100,
                order_items=299,
                order_addresses=200,
                status_history=300,
            ),
            get_profile("smoke"),
        )


def test_duplicate_history_is_rejected() -> None:
    with pytest.raises(
        RuntimeError,
        match="status_history: expected 300",
    ):
        _validate_loaded_counts(
            OrderLoadResult(
                orders=100,
                order_items=300,
                order_addresses=200,
                status_history=301,
            ),
            get_profile("smoke"),
        )
