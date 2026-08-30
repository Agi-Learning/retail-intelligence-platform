from collections import Counter

from retail_intelligence_platform.generator.domains.inventory import (
    generate_stock,
)
from retail_intelligence_platform.generator.domains.orders import (
    generate_order_items,
)
from retail_intelligence_platform.generator.domains.reservations import (
    generate_reservations,
    reservation_count,
)
from retail_intelligence_platform.generator.profiles import (
    get_profile,
)


def test_smoke_reservation_count() -> None:
    profile = get_profile("smoke")

    assert reservation_count(profile) == 270

    assert len(list(generate_reservations(profile))) == 270


def test_reservation_generation_is_deterministic() -> None:
    profile = get_profile("smoke")

    assert list(generate_reservations(profile)) == list(generate_reservations(profile))


def test_reservation_public_ids_are_unique() -> None:
    profile = get_profile("small")
    reservations = list(generate_reservations(profile))

    assert len({reservation.public_id for reservation in reservations}) == len(
        reservations
    )


def test_reservations_reference_order_items() -> None:
    profile = get_profile("smoke")

    item_keys = {
        (
            item.order_public_id,
            item.product_sku,
        )
        for item in generate_order_items(profile)
    }

    for reservation in generate_reservations(profile):
        assert (
            reservation.order_public_id,
            reservation.product_sku,
        ) in item_keys


def test_reservations_reference_existing_stock() -> None:
    profile = get_profile("smoke")

    stock_keys = {
        (
            stock.warehouse_code,
            stock.product_sku,
        )
        for stock in generate_stock(profile)
    }

    for reservation in generate_reservations(profile):
        assert (
            reservation.warehouse_code,
            reservation.product_sku,
        ) in stock_keys


def test_reservation_constraints_are_respected() -> None:
    profile = get_profile("small")

    for reservation in generate_reservations(profile):
        assert reservation.quantity > 0
        assert reservation.expires_at > reservation.created_at
        assert reservation.updated_at >= reservation.created_at


def test_reservation_status_distribution() -> None:
    profile = get_profile("smoke")

    statuses = Counter(
        reservation.status for reservation in generate_reservations(profile)
    )

    assert statuses["CONSUMED"] > 0
    assert statuses["RESERVED"] > 0
    assert statuses["RELEASED"] > 0

    assert set(statuses) <= {
        "RESERVED",
        "CONSUMED",
        "RELEASED",
    }
