from retail_intelligence_platform.generator.domains.catalog import (
    generate_brands,
    generate_categories,
    generate_product_prices,
    generate_products,
)
from retail_intelligence_platform.generator.profiles import (
    get_profile,
)


def test_smoke_catalogue_counts() -> None:
    profile = get_profile("smoke")

    assert len(list(generate_brands(profile))) == 5
    assert len(list(generate_categories(profile))) == 10
    assert len(list(generate_products(profile))) == 50

    assert len(list(generate_product_prices(profile))) == 100


def test_brand_generation_is_deterministic() -> None:
    profile = get_profile("smoke")

    first_run = list(generate_brands(profile))
    second_run = list(generate_brands(profile))

    assert first_run == second_run
    assert first_run[0].brand_name == "Retail Brand 00001"


def test_products_reference_known_dimensions() -> None:
    profile = get_profile("smoke")

    brands = {record.brand_name for record in generate_brands(profile)}

    categories = {record.category_slug for record in generate_categories(profile)}

    for product in generate_products(profile):
        assert product.category_slug in categories

        if product.brand_name is not None:
            assert product.brand_name in brands


def test_category_parents_are_generated_first() -> None:
    profile = get_profile("small")

    seen_slugs: set[str] = set()

    for category in generate_categories(profile):
        if category.parent_slug is not None:
            assert category.parent_slug in seen_slugs

        seen_slugs.add(category.category_slug)


def test_each_product_has_one_current_price() -> None:
    profile = get_profile("smoke")
    prices = list(generate_product_prices(profile))

    current_price_counts: dict[str, int] = {}

    for price in prices:
        if price.valid_to is None:
            current_price_counts[price.product_sku] = (
                current_price_counts.get(
                    price.product_sku,
                    0,
                )
                + 1
            )

        assert price.list_price >= 0

        if price.sale_price is not None:
            assert price.sale_price <= price.list_price

    assert len(current_price_counts) == 50
    assert set(current_price_counts.values()) == {1}


def test_product_constraints_are_respected() -> None:
    profile = get_profile("smoke")

    for product in generate_products(profile):
        assert product.sku == product.sku.upper()
        assert product.product_slug == (product.product_slug.lower())
        assert product.weight_grams > 0
        assert isinstance(product.attributes, dict)
