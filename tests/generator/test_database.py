import pytest

from retail_intelligence_platform.generator.config import (
    GeneratorSettings,
)
from retail_intelligence_platform.generator.database import (
    DatabaseHealth,
    validate_database_health,
)

_REQUIRED_TABLES = (
    "audit.audit_events",
    "catalog.products",
    "commerce.orders",
    "identity.customers",
    "inventory.stock",
    "outbox.events",
    "payment.payments",
)


def healthy_report() -> DatabaseHealth:
    return DatabaseHealth(
        database="retail_platform",
        user="retail_app",
        timezone="UTC",
        server_version_number=180006,
        required_tables=_REQUIRED_TABLES,
        product_select_allowed=True,
        audit_insert_allowed=True,
        audit_select_allowed=False,
    )


def test_healthy_database_is_accepted() -> None:
    settings = GeneratorSettings()

    validate_database_health(
        healthy_report(),
        settings,
    )


def test_wrong_runtime_user_is_rejected() -> None:
    settings = GeneratorSettings()

    report = DatabaseHealth(
        database="retail_platform",
        user="retail_admin",
        timezone="UTC",
        server_version_number=180006,
        required_tables=_REQUIRED_TABLES,
        product_select_allowed=True,
        audit_insert_allowed=True,
        audit_select_allowed=False,
    )

    with pytest.raises(
        RuntimeError,
        match="connected as 'retail_admin'",
    ):
        validate_database_health(report, settings)


def test_non_utc_database_is_rejected() -> None:
    settings = GeneratorSettings()

    report = DatabaseHealth(
        database="retail_platform",
        user="retail_app",
        timezone="Asia/Kolkata",
        server_version_number=180006,
        required_tables=_REQUIRED_TABLES,
        product_select_allowed=True,
        audit_insert_allowed=True,
        audit_select_allowed=False,
    )

    with pytest.raises(RuntimeError, match="UTC timezone"):
        validate_database_health(report, settings)


def test_missing_table_is_rejected() -> None:
    settings = GeneratorSettings()

    report = DatabaseHealth(
        database="retail_platform",
        user="retail_app",
        timezone="UTC",
        server_version_number=180006,
        required_tables=(
            "catalog.products",
            "identity.customers",
        ),
        product_select_allowed=True,
        audit_insert_allowed=True,
        audit_select_allowed=False,
    )

    with pytest.raises(
        RuntimeError,
        match="missing required tables",
    ):
        validate_database_health(report, settings)


def test_audit_read_access_is_rejected() -> None:
    settings = GeneratorSettings()

    report = DatabaseHealth(
        database="retail_platform",
        user="retail_app",
        timezone="UTC",
        server_version_number=180006,
        required_tables=_REQUIRED_TABLES,
        product_select_allowed=True,
        audit_insert_allowed=True,
        audit_select_allowed=True,
    )

    with pytest.raises(
        RuntimeError,
        match="must not read",
    ):
        validate_database_health(report, settings)
