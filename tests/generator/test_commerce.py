from collections import Counter

from retail_intelligence_platform.generator.domains.commerce import (
    active_cart_count,
    generate_cart_items,
    generate_carts,
)
from retail_intelligence_platform.generator.profiles import (
    get_profile,
)


def test_smoke_commerce_counts() -> None:
    profile = get_profile("smoke")

    assert active_cart_count(profile) == 2
    assert len(list(generate_carts(profile))) == 102

    assert len(list(generate_cart_items(profile))) == 306


def test_commerce_generation_is_deterministic() -> None:
    profile = get_profile("smoke")

    assert list(generate_carts(profile)) == list(generate_carts(profile))

    assert list(generate_cart_items(profile)) == list(generate_cart_items(profile))


def test_one_active_cart_per_customer_currency() -> None:
    profile = get_profile("small")

    active_keys = [
        (
            cart.customer_email,
            cart.currency_code,
        )
        for cart in generate_carts(profile)
        if cart.status == "ACTIVE"
    ]

    assert len(active_keys) == len(set(active_keys))


def test_cart_items_are_unique_per_cart() -> None:
    profile = get_profile("small")

    keys = [
        (
            item.cart_public_id,
            item.product_sku,
        )
        for item in generate_cart_items(profile)
    ]

    assert len(keys) == len(set(keys))


def test_cart_items_reference_generated_carts() -> None:
    profile = get_profile("smoke")

    cart_ids = {cart.public_id for cart in generate_carts(profile)}

    item_counts = Counter(item.cart_public_id for item in generate_cart_items(profile))

    assert set(item_counts) == cart_ids

    assert set(item_counts.values()) == {profile.average_items_per_cart}


def test_cart_and_item_constraints() -> None:
    profile = get_profile("small")

    for cart in generate_carts(profile):
        assert cart.currency_code == "INR"

        if cart.expires_at is not None:
            assert cart.expires_at > cart.created_at

    for item in generate_cart_items(profile):
        assert item.quantity > 0
        assert item.displayed_unit_price >= 0
        assert item.updated_at >= item.added_at
