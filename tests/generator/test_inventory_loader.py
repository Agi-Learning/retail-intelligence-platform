import pytest

from retail_intelligence_platform.generator.loaders.inventory import (
    InventoryLoadResult,
    _validate_loaded_counts,
)
from retail_intelligence_platform.generator.profiles import (
    get_profile,
)


def test_inventory_result_total() -> None:
    result = InventoryLoadResult(
        warehouses=3,
        stock=100,
        reorder_required=10,
    )

    assert result.total_rows == 103


def test_smoke_inventory_counts_are_valid() -> None:
    result = InventoryLoadResult(
        warehouses=3,
        stock=100,
        reorder_required=10,
    )

    _validate_loaded_counts(
        result,
        get_profile("smoke"),
    )


def test_missing_stock_is_rejected() -> None:
    result = InventoryLoadResult(
        warehouses=3,
        stock=99,
        reorder_required=10,
    )

    with pytest.raises(
        RuntimeError,
        match="stock: expected 100",
    ):
        _validate_loaded_counts(
            result,
            get_profile("smoke"),
        )


def test_missing_reorder_scenario_is_rejected() -> None:
    result = InventoryLoadResult(
        warehouses=3,
        stock=100,
        reorder_required=0,
    )

    with pytest.raises(
        RuntimeError,
        match="reorder scenario",
    ):
        _validate_loaded_counts(
            result,
            get_profile("smoke"),
        )
