import pytest

from retail_intelligence_platform.generator.profiles import (
    GenerationProfile,
    available_profiles,
    get_profile,
)


def test_available_profiles_are_in_scale_order() -> None:
    assert available_profiles() == (
        "smoke",
        "small",
        "medium",
        "large",
        "stress",
    )


def test_profile_lookup_is_case_insensitive() -> None:
    profile = get_profile(" MEDIUM ")

    assert profile.name == "medium"
    assert profile.customer_count == 250_000
    assert profile.order_count == 2_000_000


def test_estimated_rows_include_all_business_tables() -> None:
    profile = get_profile("smoke")

    assert len(profile.estimated_rows) == 21
    assert profile.estimated_rows["identity.customers"] == 20
    assert profile.estimated_rows["identity.addresses"] == 40
    assert profile.estimated_rows["catalog.product_prices"] == 100
    assert profile.estimated_rows["commerce.orders"] == 100
    assert profile.estimated_rows["commerce.order_items"] == 300


def test_profile_estimates_are_deterministic() -> None:
    first = get_profile("small").estimated_total_rows
    second = get_profile("small").estimated_total_rows

    assert first == second
    assert first > 0


def test_unknown_profile_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Unknown profile 'enormous'",
    ):
        get_profile("enormous")


def test_invalid_ratio_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="active_cart_ratio",
    ):
        GenerationProfile(
            name="invalid",
            seed=1,
            customer_count=1,
            brand_count=1,
            category_count=1,
            product_count=1,
            warehouse_count=1,
            order_count=1,
            active_cart_ratio=1.5,
        )


def test_warehouse_distribution_is_validated() -> None:
    with pytest.raises(
        ValueError,
        match="warehouses_per_product",
    ):
        GenerationProfile(
            name="invalid",
            seed=1,
            customer_count=1,
            brand_count=1,
            category_count=1,
            product_count=1,
            warehouse_count=2,
            order_count=1,
            warehouses_per_product=3,
        )
