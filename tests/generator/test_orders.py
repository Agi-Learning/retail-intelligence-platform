from collections import Counter, defaultdict
from itertools import pairwise

from retail_intelligence_platform.generator.domains.orders import (
    generate_order_addresses,
    generate_order_items,
    generate_order_status_history,
    generate_orders,
)
from retail_intelligence_platform.generator.profiles import (
    get_profile,
)


def test_smoke_order_counts() -> None:
    profile = get_profile("smoke")

    assert len(list(generate_orders(profile))) == 100
    assert len(list(generate_order_items(profile))) == 300

    assert len(list(generate_order_addresses(profile))) == 200

    assert len(list(generate_order_status_history(profile))) == 300


def test_order_generation_is_deterministic() -> None:
    profile = get_profile("smoke")

    assert list(generate_orders(profile)) == list(generate_orders(profile))

    assert list(generate_order_items(profile)) == list(generate_order_items(profile))


def test_order_business_keys_are_unique() -> None:
    profile = get_profile("small")
    orders = list(generate_orders(profile))

    assert len({order.public_id for order in orders}) == len(orders)

    assert len({order.order_number for order in orders}) == len(orders)

    assert len({order.idempotency_key for order in orders}) == len(orders)

    assert len({order.cart_public_id for order in orders}) == len(orders)


def test_order_monetary_totals_are_consistent() -> None:
    profile = get_profile("small")

    for order in generate_orders(profile):
        assert order.subtotal_amount >= 0
        assert order.discount_amount >= 0
        assert order.discount_amount <= order.subtotal_amount
        assert order.tax_amount >= 0
        assert order.shipping_amount >= 0

        assert order.total_amount == (
            order.subtotal_amount
            - order.discount_amount
            + order.tax_amount
            + order.shipping_amount
        )


def test_order_item_totals_are_consistent() -> None:
    profile = get_profile("small")

    for item in generate_order_items(profile):
        assert item.quantity > 0
        assert item.unit_price >= 0
        assert item.discount_amount >= 0
        assert item.tax_amount >= 0

        assert item.line_total == (
            item.quantity * item.unit_price - item.discount_amount + item.tax_amount
        )


def test_each_order_has_required_snapshots() -> None:
    profile = get_profile("smoke")

    item_counts = Counter(
        item.order_public_id for item in generate_order_items(profile)
    )

    address_roles = defaultdict(set)

    for address in generate_order_addresses(profile):
        address_roles[address.order_public_id].add(address.address_role)

    assert set(item_counts.values()) == {3}

    assert all(roles == {"BILLING", "SHIPPING"} for roles in address_roles.values())


def test_status_history_matches_final_order_state() -> None:
    profile = get_profile("smoke")

    histories = defaultdict(list)

    for history in generate_order_status_history(profile):
        histories[history.order_public_id].append(history)

    for order in generate_orders(profile):
        order_history = histories[order.public_id]

        assert len(order_history) == 3
        assert order_history[0].previous_status is None
        assert order_history[-1].new_status == order.status

        for previous, current in pairwise(order_history):
            assert current.previous_status == previous.new_status
