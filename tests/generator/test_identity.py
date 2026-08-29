from collections import Counter

from retail_intelligence_platform.generator.domains.identity import (
    generate_addresses,
    generate_credentials,
    generate_customers,
)
from retail_intelligence_platform.generator.profiles import (
    get_profile,
)


def test_smoke_identity_counts() -> None:
    profile = get_profile("smoke")

    assert len(list(generate_customers(profile))) == 20
    assert len(list(generate_credentials(profile))) == 20
    assert len(list(generate_addresses(profile))) == 40


def test_customer_generation_is_deterministic() -> None:
    profile = get_profile("smoke")

    assert list(generate_customers(profile)) == list(generate_customers(profile))


def test_customer_emails_and_ids_are_unique() -> None:
    profile = get_profile("small")
    customers = list(generate_customers(profile))

    emails = {customer.email for customer in customers}

    public_ids = {customer.public_id for customer in customers}

    assert len(emails) == profile.customer_count
    assert len(public_ids) == profile.customer_count


def test_customer_fields_respect_constraints() -> None:
    profile = get_profile("small")

    for customer in generate_customers(profile):
        assert customer.first_name.strip()
        assert customer.email == (customer.email.lower().strip())
        assert len(customer.email) >= 3
        assert customer.phone_number.strip()

        if customer.last_name is not None:
            assert customer.last_name.strip()


def test_credentials_are_not_plaintext() -> None:
    profile = get_profile("smoke")

    for credential in generate_credentials(profile):
        assert credential.password_hash.startswith("$synthetic$sha256$")
        assert len(credential.password_hash) >= 20
        assert credential.failed_attempts >= 0

        if credential.locked_until is not None:
            assert credential.locked_until >= credential.password_changed_at


def test_addresses_reference_customers() -> None:
    profile = get_profile("smoke")

    customer_emails = {customer.email for customer in generate_customers(profile)}

    for address in generate_addresses(profile):
        assert address.customer_email in customer_emails
        assert address.recipient_name.strip()
        assert address.address_line_1.strip()
        assert address.city.strip()
        assert address.state_region.strip()
        assert address.postal_code.strip()
        assert address.country_code == "IN"


def test_one_default_address_per_customer() -> None:
    profile = get_profile("small")

    default_counts = Counter(
        address.customer_email
        for address in generate_addresses(profile)
        if address.is_default
    )

    assert len(default_counts) == profile.customer_count
    assert set(default_counts.values()) == {1}


def test_seed_override_is_reproducible() -> None:
    profile = get_profile("smoke")

    first = list(
        generate_customers(
            profile,
            seed=123,
        )
    )

    second = list(
        generate_customers(
            profile,
            seed=123,
        )
    )

    different = list(
        generate_customers(
            profile,
            seed=456,
        )
    )

    assert first == second
    assert first != different
