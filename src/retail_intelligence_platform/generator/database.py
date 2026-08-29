"""PostgreSQL connectivity and runtime safety checks."""

from dataclasses import dataclass

import psycopg

from retail_intelligence_platform.generator.config import (
    GeneratorSettings,
)

_REQUIRED_TABLES = (
    "identity.customers",
    "catalog.products",
    "inventory.stock",
    "commerce.orders",
    "payment.payments",
    "outbox.events",
    "audit.audit_events",
)


@dataclass(frozen=True, slots=True)
class DatabaseHealth:
    """Safe database health information."""

    database: str
    user: str
    timezone: str
    server_version_number: int
    required_tables: tuple[str, ...]
    product_select_allowed: bool
    audit_insert_allowed: bool
    audit_select_allowed: bool


def check_database(
    settings: GeneratorSettings,
) -> DatabaseHealth:
    """Connect as the runtime role and inspect safe metadata."""

    password = settings.load_password()

    with (
        psycopg.connect(
            host=settings.host,
            port=settings.port,
            dbname=settings.database,
            user=settings.user,
            password=password.get_secret_value(),
            connect_timeout=settings.connect_timeout_seconds,
            application_name="retail-data-generator",
        ) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            """
                SELECT
                    current_database(),
                    current_user,
                    current_setting('TimeZone'),
                    current_setting(
                        'server_version_num'
                    )::INTEGER,
                    has_table_privilege(
                        current_user,
                        'catalog.products',
                        'SELECT'
                    ),
                    has_table_privilege(
                        current_user,
                        'audit.audit_events',
                        'INSERT'
                    ),
                    has_table_privilege(
                        current_user,
                        'audit.audit_events',
                        'SELECT'
                    );
                """
        )

        metadata = cursor.fetchone()

        if metadata is None:
            raise RuntimeError("Database metadata query returned no result")

        cursor.execute(
            """
                SELECT qualified_name
                FROM unnest(%s::TEXT[]) AS required(
                    qualified_name
                )
                WHERE to_regclass(qualified_name) IS NOT NULL
                ORDER BY qualified_name;
                """,
            (list(_REQUIRED_TABLES),),
        )

        available_tables = tuple(row[0] for row in cursor.fetchall())

    health = DatabaseHealth(
        database=metadata[0],
        user=metadata[1],
        timezone=metadata[2],
        server_version_number=metadata[3],
        required_tables=available_tables,
        product_select_allowed=metadata[4],
        audit_insert_allowed=metadata[5],
        audit_select_allowed=metadata[6],
    )

    validate_database_health(health, settings)

    return health


def validate_database_health(
    health: DatabaseHealth,
    settings: GeneratorSettings,
) -> None:
    """Reject connections that do not match safety expectations."""

    errors: list[str] = []

    if health.database != settings.database:
        errors.append(
            f"expected database {settings.database!r}, connected to {health.database!r}"
        )

    if health.user != settings.user:
        errors.append(f"expected user {settings.user!r}, connected as {health.user!r}")

    if health.timezone.upper() != "UTC":
        errors.append(f"expected UTC timezone, found {health.timezone!r}")

    missing_tables = sorted(set(_REQUIRED_TABLES) - set(health.required_tables))

    if missing_tables:
        errors.append("missing required tables: " + ", ".join(missing_tables))

    if not health.product_select_allowed:
        errors.append("runtime role cannot read catalog.products")

    if not health.audit_insert_allowed:
        errors.append("runtime role cannot insert audit.audit_events")

    if health.audit_select_allowed:
        errors.append("runtime role must not read audit.audit_events")

    if errors:
        formatted_errors = "\n- ".join(errors)

        raise RuntimeError(f"Database health validation failed:\n- {formatted_errors}")
