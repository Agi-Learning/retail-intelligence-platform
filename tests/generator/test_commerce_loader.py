import pytest

from retail_intelligence_platform.generator.loaders.commerce import (
    CommerceLoadResult,
    _validate_loaded_counts,
)
from retail_intelligence_platform.generator.profiles import (
    get_profile,
)


def test_commerce_result_total() -> None:
    result = CommerceLoadResult(
        carts=102,
        cart_items=306,
        active_carts=2,
    )

    assert result.total_rows == 408


def test_smoke_commerce_counts_are_valid() -> None:
    _validate_loaded_counts(
        CommerceLoadResult(
            carts=102,
            cart_items=306,
            active_carts=2,
        ),
        get_profile("smoke"),
    )


def test_missing_cart_items_are_rejected() -> None:
    with pytest.raises(
        RuntimeError,
        match="cart_items: expected 306",
    ):
        _validate_loaded_counts(
            CommerceLoadResult(
                carts=102,
                cart_items=305,
                active_carts=2,
            ),
            get_profile("smoke"),
        )


def test_duplicate_active_cart_count_is_rejected() -> None:
    with pytest.raises(
        RuntimeError,
        match="active_carts: expected 2",
    ):
        _validate_loaded_counts(
            CommerceLoadResult(
                carts=102,
                cart_items=306,
                active_carts=3,
            ),
            get_profile("smoke"),
        )
