from retail_intelligence_platform.generator.domains.inventory import (
    generate_stock,
    generate_warehouses,
)
from retail_intelligence_platform.generator.profiles import (
    get_profile,
)


def test_smoke_inventory_counts() -> None:
    profile = get_profile("smoke")

    warehouses = list(generate_warehouses(profile))
    stock = list(generate_stock(profile))

    assert len(warehouses) == 3
    assert len(stock) == 100


def test_inventory_generation_is_deterministic() -> None:
    profile = get_profile("smoke")

    assert list(generate_warehouses(profile)) == list(generate_warehouses(profile))

    assert list(generate_stock(profile)) == list(generate_stock(profile))


def test_stock_keys_are_unique() -> None:
    profile = get_profile("small")

    keys = [
        (
            record.warehouse_code,
            record.product_sku,
        )
        for record in generate_stock(profile)
    ]

    assert len(keys) == len(set(keys))


def test_stock_references_generated_dimensions() -> None:
    profile = get_profile("smoke")

    warehouse_codes = {record.warehouse_code for record in generate_warehouses(profile)}

    product_skus = {
        f"SKU-{number:08d}"
        for number in range(
            1,
            profile.product_count + 1,
        )
    }

    for record in generate_stock(profile):
        assert record.warehouse_code in warehouse_codes
        assert record.product_sku in product_skus


def test_stock_quantities_respect_constraints() -> None:
    profile = get_profile("small")

    for record in generate_stock(profile):
        assert record.on_hand_quantity >= 0
        assert record.reserved_quantity >= 0
        assert record.reserved_quantity <= record.on_hand_quantity
        assert record.available_quantity >= 0
        assert record.reorder_level >= 0


def test_stock_contains_reorder_scenarios() -> None:
    profile = get_profile("smoke")
    stock = list(generate_stock(profile))

    assert any(record.requires_reorder for record in stock)

    assert any(not record.requires_reorder for record in stock)


def test_warehouse_fields_respect_constraints() -> None:
    profile = get_profile("smoke")

    for warehouse in generate_warehouses(profile):
        assert warehouse.warehouse_code == (warehouse.warehouse_code.upper())
        assert warehouse.country_code == "IN"
        assert warehouse.city.strip()
        assert warehouse.state_region.strip()
        assert warehouse.postal_code.strip()
