"""Deterministic customer identity record generation."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from faker import Faker

from retail_intelligence_platform.generator.profiles import (
    GenerationProfile,
)

_IDENTITY_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "retail-intelligence-platform/identity",
)

_REGISTRATION_START = datetime(
    2024,
    1,
    1,
    tzinfo=UTC,
)

_LOCATIONS = (
    ("Chennai", "Tamil Nadu", "600001"),
    ("Bengaluru", "Karnataka", "560001"),
    ("Hyderabad", "Telangana", "500001"),
    ("Mumbai", "Maharashtra", "400001"),
    ("Delhi", "Delhi", "110001"),
    ("Kolkata", "West Bengal", "700001"),
    ("Pune", "Maharashtra", "411001"),
    ("Ahmedabad", "Gujarat", "380001"),
)

_ADDRESS_TYPES = (
    "HOME",
    "WORK",
    "SHIPPING",
    "OTHER",
)


@dataclass(frozen=True, slots=True)
class CustomerRecord:
    public_id: UUID
    first_name: str
    last_name: str | None
    email: str
    phone_number: str
    status: str
    registered_at: datetime
    last_login_at: datetime | None


@dataclass(frozen=True, slots=True)
class CredentialRecord:
    customer_email: str
    password_hash: str
    password_changed_at: datetime
    failed_attempts: int
    locked_until: datetime | None


@dataclass(frozen=True, slots=True)
class AddressRecord:
    public_id: UUID
    customer_email: str
    address_type: str
    recipient_name: str
    phone_number: str
    address_line_1: str
    address_line_2: str | None
    city: str
    state_region: str
    postal_code: str
    country_code: str
    is_default: bool


def stable_identity_uuid(
    entity_type: str,
    sequence_key: str,
) -> UUID:
    """Create a reproducible identity-domain UUID."""

    return uuid5(
        _IDENTITY_NAMESPACE,
        f"{entity_type}:{sequence_key}",
    )


def customer_email(sequence_number: int) -> str:
    """Return a unique normalized synthetic email."""

    return f"customer-{sequence_number:09d}@example.test"


def customer_phone(sequence_number: int) -> str:
    """Return a unique synthetic Indian phone number."""

    return f"+919{sequence_number:09d}"


def _customer_status(sequence_number: int) -> str:
    if sequence_number % 1_000 == 0:
        return "CLOSED"

    if sequence_number % 250 == 0:
        return "SUSPENDED"

    if sequence_number % 100 == 0:
        return "LOCKED"

    if sequence_number % 20 == 0:
        return "PENDING"

    return "ACTIVE"


def generate_customers(
    profile: GenerationProfile,
    seed: int | None = None,
) -> Iterator[CustomerRecord]:
    """Yield deterministic customer profiles."""

    faker = Faker("en_IN")
    faker.seed_instance(profile.seed if seed is None else seed)

    for sequence_number in range(
        1,
        profile.customer_count + 1,
    ):
        first_name = faker.first_name()
        generated_last_name = faker.last_name()

        registered_at = _REGISTRATION_START + timedelta(minutes=sequence_number)

        yield CustomerRecord(
            public_id=stable_identity_uuid(
                "customer",
                str(sequence_number),
            ),
            first_name=first_name.strip(),
            last_name=(
                None if sequence_number % 25 == 0 else generated_last_name.strip()
            ),
            email=customer_email(sequence_number),
            phone_number=customer_phone(sequence_number),
            status=_customer_status(sequence_number),
            registered_at=registered_at,
            last_login_at=(
                None
                if sequence_number % 10 == 0
                else registered_at
                + timedelta(
                    days=sequence_number % 365,
                    minutes=5,
                )
            ),
        )


def generate_credentials(
    profile: GenerationProfile,
) -> Iterator[CredentialRecord]:
    """Yield non-usable deterministic hash placeholders."""

    for sequence_number in range(
        1,
        profile.customer_count + 1,
    ):
        registered_at = _REGISTRATION_START + timedelta(minutes=sequence_number)

        synthetic_digest = sha256(
            (f"retail-synthetic-credential:{sequence_number}").encode()
        ).hexdigest()

        is_locked = sequence_number % 100 == 0

        yield CredentialRecord(
            customer_email=customer_email(sequence_number),
            password_hash=(f"$synthetic$sha256${synthetic_digest}"),
            password_changed_at=registered_at,
            failed_attempts=5 if is_locked else 0,
            locked_until=(registered_at + timedelta(days=1) if is_locked else None),
        )


def generate_addresses(
    profile: GenerationProfile,
    seed: int | None = None,
) -> Iterator[AddressRecord]:
    """Yield deterministic reusable customer addresses."""

    customers = generate_customers(
        profile,
        seed=seed,
    )

    for sequence_number, customer in enumerate(
        customers,
        start=1,
    ):
        recipient_name = " ".join(
            part
            for part in (
                customer.first_name,
                customer.last_name,
            )
            if part
        )

        for address_index in range(profile.addresses_per_customer):
            location_number = sequence_number + address_index - 1

            city, state_region, base_postal_code = _LOCATIONS[
                location_number % len(_LOCATIONS)
            ]

            address_type = _ADDRESS_TYPES[address_index % len(_ADDRESS_TYPES)]

            address_key = f"{sequence_number}:{address_index + 1}"

            yield AddressRecord(
                public_id=stable_identity_uuid(
                    "address",
                    address_key,
                ),
                customer_email=customer.email,
                address_type=address_type,
                recipient_name=recipient_name,
                phone_number=customer.phone_number,
                address_line_1=(
                    f"{sequence_number}, Retail Residency Block {address_index + 1}"
                ),
                address_line_2=(
                    None if address_index % 2 == 0 else "Near Central Market"
                ),
                city=city,
                state_region=state_region,
                postal_code=base_postal_code,
                country_code="IN",
                is_default=address_index == 0,
            )
