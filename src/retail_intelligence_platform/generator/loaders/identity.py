"""Transactional loading for customer identity records."""

from collections.abc import Iterable
from dataclasses import dataclass

import psycopg

from retail_intelligence_platform.generator.config import (
    GeneratorSettings,
)
from retail_intelligence_platform.generator.domains.identity import (
    AddressRecord,
    CredentialRecord,
    CustomerRecord,
    generate_addresses,
    generate_credentials,
    generate_customers,
)
from retail_intelligence_platform.generator.loaders.catalog import (
    batched,
)
from retail_intelligence_platform.generator.profiles import (
    GenerationProfile,
)


@dataclass(frozen=True, slots=True)
class IdentityLoadResult:
    customers: int
    credentials: int
    addresses: int
    default_addresses: int

    @property
    def total_rows(self) -> int:
        return self.customers + self.credentials + self.addresses


def load_identity(
    settings: GeneratorSettings,
    profile: GenerationProfile,
) -> IdentityLoadResult:
    """Load identity records in one transaction."""

    password = settings.load_password()

    with (
        psycopg.connect(
            host=settings.host,
            port=settings.port,
            dbname=settings.database,
            user=settings.user,
            password=password.get_secret_value(),
            connect_timeout=(settings.connect_timeout_seconds),
            application_name="retail-identity-loader",
        ) as connection,
        connection.cursor() as cursor,
    ):
        _load_customers(
            cursor,
            generate_customers(
                profile,
                seed=settings.seed,
            ),
            settings.batch_size,
        )

        _load_credentials(
            cursor,
            generate_credentials(profile),
            settings.batch_size,
        )

        _load_addresses(
            cursor,
            generate_addresses(
                profile,
                seed=settings.seed,
            ),
            settings.batch_size,
        )

        result = _read_generated_counts(cursor)

        _validate_loaded_counts(
            result,
            profile,
        )

        connection.commit()

    return result


def _load_customers(
    cursor: psycopg.Cursor,
    records: Iterable[CustomerRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO identity.customers (
            public_id,
            first_name,
            last_name,
            email,
            phone_number,
            status,
            registered_at,
            last_login_at,
            created_at,
            updated_at
        )
        VALUES (
            %(public_id)s,
            %(first_name)s,
            %(last_name)s,
            %(email)s,
            %(phone_number)s,
            %(status)s,
            %(registered_at)s,
            %(last_login_at)s,
            %(registered_at)s,
            %(registered_at)s
        )
        ON CONFLICT (email)
        DO UPDATE SET
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            phone_number = EXCLUDED.phone_number,
            status = EXCLUDED.status,
            registered_at = EXCLUDED.registered_at,
            last_login_at = EXCLUDED.last_login_at,
            updated_at = clock_timestamp(),
            version = identity.customers.version + 1;
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "public_id": record.public_id,
                    "first_name": record.first_name,
                    "last_name": record.last_name,
                    "email": record.email,
                    "phone_number": (record.phone_number),
                    "status": record.status,
                    "registered_at": (record.registered_at),
                    "last_login_at": (record.last_login_at),
                }
                for record in batch
            ],
        )


def _load_credentials(
    cursor: psycopg.Cursor,
    records: Iterable[CredentialRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO identity.credentials (
            customer_id,
            password_hash,
            password_changed_at,
            failed_attempts,
            locked_until,
            created_at,
            updated_at
        )
        SELECT
            customer.customer_id,
            %(password_hash)s,
            %(password_changed_at)s,
            %(failed_attempts)s,
            %(locked_until)s,
            %(password_changed_at)s,
            %(password_changed_at)s
        FROM identity.customers AS customer
        WHERE customer.email = %(customer_email)s
        ON CONFLICT (customer_id)
        DO UPDATE SET
            password_hash = EXCLUDED.password_hash,
            password_changed_at =
                EXCLUDED.password_changed_at,
            failed_attempts =
                EXCLUDED.failed_attempts,
            locked_until = EXCLUDED.locked_until,
            updated_at = clock_timestamp();
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "customer_email": (record.customer_email),
                    "password_hash": (record.password_hash),
                    "password_changed_at": (record.password_changed_at),
                    "failed_attempts": (record.failed_attempts),
                    "locked_until": (record.locked_until),
                }
                for record in batch
            ],
        )


def _load_addresses(
    cursor: psycopg.Cursor,
    records: Iterable[AddressRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO identity.addresses (
            public_id,
            customer_id,
            address_type,
            recipient_name,
            phone_number,
            address_line_1,
            address_line_2,
            city,
            state_region,
            postal_code,
            country_code,
            is_default,
            created_at,
            updated_at
        )
        SELECT
            %(public_id)s,
            customer.customer_id,
            %(address_type)s,
            %(recipient_name)s,
            %(phone_number)s,
            %(address_line_1)s,
            %(address_line_2)s,
            %(city)s,
            %(state_region)s,
            %(postal_code)s,
            %(country_code)s,
            %(is_default)s,
            customer.registered_at,
            customer.registered_at
        FROM identity.customers AS customer
        WHERE customer.email = %(customer_email)s
        ON CONFLICT (public_id)
        DO UPDATE SET
            address_type = EXCLUDED.address_type,
            recipient_name = EXCLUDED.recipient_name,
            phone_number = EXCLUDED.phone_number,
            address_line_1 = EXCLUDED.address_line_1,
            address_line_2 = EXCLUDED.address_line_2,
            city = EXCLUDED.city,
            state_region = EXCLUDED.state_region,
            postal_code = EXCLUDED.postal_code,
            country_code = EXCLUDED.country_code,
            is_default = EXCLUDED.is_default,
            updated_at = clock_timestamp();
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "public_id": record.public_id,
                    "customer_email": (record.customer_email),
                    "address_type": (record.address_type),
                    "recipient_name": (record.recipient_name),
                    "phone_number": (record.phone_number),
                    "address_line_1": (record.address_line_1),
                    "address_line_2": (record.address_line_2),
                    "city": record.city,
                    "state_region": (record.state_region),
                    "postal_code": (record.postal_code),
                    "country_code": (record.country_code),
                    "is_default": (record.is_default),
                }
                for record in batch
            ],
        )


def _read_generated_counts(
    cursor: psycopg.Cursor,
) -> IdentityLoadResult:
    cursor.execute(
        """
        SELECT
            (
                SELECT count(*)
                FROM identity.customers
                WHERE email LIKE
                    'customer-%@example.test'
            ),
            (
                SELECT count(*)
                FROM identity.credentials AS credential
                JOIN identity.customers AS customer
                  ON customer.customer_id =
                     credential.customer_id
                WHERE customer.email LIKE
                    'customer-%@example.test'
            ),
            (
                SELECT count(*)
                FROM identity.addresses AS address
                JOIN identity.customers AS customer
                  ON customer.customer_id =
                     address.customer_id
                WHERE customer.email LIKE
                    'customer-%@example.test'
            ),
            (
                SELECT count(*)
                FROM identity.addresses AS address
                JOIN identity.customers AS customer
                  ON customer.customer_id =
                     address.customer_id
                WHERE customer.email LIKE
                          'customer-%@example.test'
                  AND address.is_default = TRUE
                  AND address.deleted_at IS NULL
            );
        """
    )

    row = cursor.fetchone()

    if row is None:
        raise RuntimeError("Identity count query returned no result")

    return IdentityLoadResult(
        customers=row[0],
        credentials=row[1],
        addresses=row[2],
        default_addresses=row[3],
    )


def _validate_loaded_counts(
    result: IdentityLoadResult,
    profile: GenerationProfile,
) -> None:
    expected = {
        "customers": profile.customer_count,
        "credentials": profile.customer_count,
        "addresses": (profile.customer_count * profile.addresses_per_customer),
        "default_addresses": profile.customer_count,
    }

    actual = {
        "customers": result.customers,
        "credentials": result.credentials,
        "addresses": result.addresses,
        "default_addresses": (result.default_addresses),
    }

    errors = [
        f"{name}: expected {expected[name]}, found {actual[name]}"
        for name in expected
        if actual[name] != expected[name]
    ]

    if errors:
        raise RuntimeError(
            "Identity row-count validation failed:\n- " + "\n- ".join(errors)
        )
