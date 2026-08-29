import pytest

from retail_intelligence_platform.generator.loaders.catalog import (
    CatalogLoadResult,
    batched,
)


def test_batched_preserves_order() -> None:
    result = list(
        batched(
            range(7),
            batch_size=3,
        )
    )

    assert result == [
        [0, 1, 2],
        [3, 4, 5],
        [6],
    ]


def test_batched_handles_empty_input() -> None:
    assert list(batched([], batch_size=10)) == []


def test_batched_rejects_invalid_size() -> None:
    with pytest.raises(
        ValueError,
        match="batch_size must be positive",
    ):
        list(batched([1], batch_size=0))


def test_catalog_result_total() -> None:
    result = CatalogLoadResult(
        brands=5,
        categories=10,
        products=50,
        product_prices=100,
    )

    assert result.total_rows == 165
