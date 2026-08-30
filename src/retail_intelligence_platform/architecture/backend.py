"""Spring Boot implementation contracts for enterprise services."""

from collections import Counter
from csv import DictReader, DictWriter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

EXPECTED_SERVICES = 1_000
EXPECTED_TABLES = 10_000
EXPECTED_FULL_CDC_TABLES = 9_802
EXPECTED_EXCLUDED_CDC_TABLES = 198
EXPECTED_RELATIONSHIPS = 6_040

JAVA_VERSION = "25"
SPRING_BOOT_VERSION = "4.1.1"
GRADLE_VERSION = "9.7.1"

BACKEND_CONTRACT_COLUMNS = (
    "planning_lesson",
    "implementation_lesson",
    "domain_id",
    "domain",
    "microservice_id",
    "microservice_name",
    "service_archetype",
    "team_id",
    "java_version",
    "spring_boot_version",
    "build_tool",
    "gradle_version",
    "build_dsl",
    "packaging",
    "java_package",
    "application_class",
    "backend_module_path",
    "api_base_path",
    "api_access_policy",
    "customer_auth_audience",
    "admin_auth_audience",
    "web_stack",
    "api_contract",
    "security_stack",
    "persistence_stack",
    "database_engine",
    "database_name",
    "schema_name",
    "migration_tool",
    "owned_table_count",
    "full_cdc_table_count",
    "excluded_cdc_table_count",
    "outgoing_relationship_count",
    "incoming_relationship_count",
    "event_outgoing_count",
    "event_incoming_count",
    "colocated_validation_count",
    "kafka_producer_required",
    "kafka_consumer_required",
    "outbox_required",
    "dlq_consumer_required",
    "resilience_stack",
    "observability_stack",
    "testing_stack",
    "container_strategy",
    "deployment_unit",
    "deployment_namespace",
    "implementation_status",
)


class BackendContractError(ValueError):
    """Raised when a backend contract is incomplete."""


@dataclass(frozen=True, slots=True)
class BackendContractSummary:
    """Validated measurements from all backend contracts."""

    services: int
    shared_api_services: int
    customer_api_services: int
    admin_api_services: int
    internal_platform_services: int
    owned_tables: int
    full_cdc_tables: int
    excluded_cdc_tables: int
    outgoing_relationships: int
    incoming_relationships: int
    event_producer_services: int
    event_consumer_services: int
    colocated_validator_services: int


def write_backend_contract_manifest(
    service_manifest_path: Path,
    frontend_policy_path: Path,
    relationship_manifest_path: Path,
    destination: Path,
) -> int:
    """Write one Spring Boot contract per microservice."""

    services = _read_csv(service_manifest_path)
    policies = {row["domain"]: row for row in _read_csv(frontend_policy_path)}
    relationships = _read_csv(relationship_manifest_path)

    if len(services) != EXPECTED_SERVICES:
        raise BackendContractError(
            f"Expected {EXPECTED_SERVICES} services, found {len(services)}"
        )

    if len(relationships) != EXPECTED_RELATIONSHIPS:
        raise BackendContractError(
            f"Expected {EXPECTED_RELATIONSHIPS} relationships, "
            f"found {len(relationships)}"
        )

    service_names = {service["microservice_name"] for service in services}

    relationship_services = {
        relationship[f"{side}_service"]
        for relationship in relationships
        for side in ("source", "target")
    }

    missing_services = relationship_services - service_names

    if missing_services:
        raise BackendContractError(
            f"Unknown relationship services: {sorted(missing_services)}"
        )

    rows = [
        _build_contract(
            service,
            policies[service["domain"]],
            relationships,
        )
        for service in services
    ]

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with destination.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = DictWriter(
            stream,
            fieldnames=BACKEND_CONTRACT_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(cast(Any, rows))

    return len(rows)


def validate_backend_contract_manifest(
    path: Path,
) -> BackendContractSummary:
    """Validate all Spring Boot service contracts."""

    with path.open(
        newline="",
        encoding="utf-8",
    ) as stream:
        reader = DictReader(stream)
        rows = list(reader)
        columns = tuple(reader.fieldnames or ())

    if columns != BACKEND_CONTRACT_COLUMNS:
        raise BackendContractError("Unexpected backend contract columns")

    if len(rows) != EXPECTED_SERVICES:
        raise BackendContractError(
            f"Expected {EXPECTED_SERVICES} contracts, found {len(rows)}"
        )

    _require_unique(
        rows,
        "microservice_id",
    )
    _require_unique(
        rows,
        "backend_module_path",
    )
    _require_unique(
        rows,
        "api_base_path",
    )
    _require_unique(
        rows,
        "java_package",
    )
    _require_unique(
        rows,
        "deployment_unit",
    )

    _validate_rows(rows)

    archetypes = Counter(row["service_archetype"] for row in rows)

    expected_archetypes = {
        "SHARED_API_SERVICE": 300,
        "CUSTOMER_API_SERVICE": 50,
        "ADMIN_API_SERVICE": 430,
        "INTERNAL_PLATFORM_SERVICE": 220,
    }

    if dict(archetypes) != expected_archetypes:
        raise BackendContractError(f"Unexpected archetypes: {dict(archetypes)}")

    owned_tables = _sum(rows, "owned_table_count")
    full_cdc_tables = _sum(
        rows,
        "full_cdc_table_count",
    )
    excluded_cdc_tables = _sum(
        rows,
        "excluded_cdc_table_count",
    )
    outgoing_relationships = _sum(
        rows,
        "outgoing_relationship_count",
    )
    incoming_relationships = _sum(
        rows,
        "incoming_relationship_count",
    )

    expected_totals = {
        "owned tables": (
            owned_tables,
            EXPECTED_TABLES,
        ),
        "full CDC tables": (
            full_cdc_tables,
            EXPECTED_FULL_CDC_TABLES,
        ),
        "excluded CDC tables": (
            excluded_cdc_tables,
            EXPECTED_EXCLUDED_CDC_TABLES,
        ),
        "outgoing relationships": (
            outgoing_relationships,
            EXPECTED_RELATIONSHIPS,
        ),
        "incoming relationships": (
            incoming_relationships,
            EXPECTED_RELATIONSHIPS,
        ),
    }

    for name, (actual, expected) in expected_totals.items():
        if actual != expected:
            raise BackendContractError(f"Expected {expected} {name}, found {actual}")

    return BackendContractSummary(
        services=len(rows),
        shared_api_services=archetypes["SHARED_API_SERVICE"],
        customer_api_services=archetypes["CUSTOMER_API_SERVICE"],
        admin_api_services=archetypes["ADMIN_API_SERVICE"],
        internal_platform_services=archetypes["INTERNAL_PLATFORM_SERVICE"],
        owned_tables=owned_tables,
        full_cdc_tables=full_cdc_tables,
        excluded_cdc_tables=excluded_cdc_tables,
        outgoing_relationships=outgoing_relationships,
        incoming_relationships=incoming_relationships,
        event_producer_services=sum(
            row["kafka_producer_required"] == "Y" for row in rows
        ),
        event_consumer_services=sum(
            row["kafka_consumer_required"] == "Y" for row in rows
        ),
        colocated_validator_services=sum(
            int(row["colocated_validation_count"]) > 0 for row in rows
        ),
    )


def _build_contract(
    service: dict[str, str],
    policy: dict[str, str],
    relationships: list[dict[str, str]],
) -> dict[str, str]:
    service_name = service["microservice_name"]

    outgoing = [
        relationship
        for relationship in relationships
        if relationship["source_service"] == service_name
    ]

    incoming = [
        relationship
        for relationship in relationships
        if relationship["target_service"] == service_name
    ]

    event_outgoing = [
        relationship
        for relationship in outgoing
        if relationship["effective_implementation"] == "EVENT_DRIVEN_LOGICAL_REFERENCE"
    ]

    event_incoming = [
        relationship
        for relationship in incoming
        if relationship["effective_implementation"] == "EVENT_DRIVEN_LOGICAL_REFERENCE"
    ]

    colocated = [
        relationship
        for relationship in outgoing
        if relationship["effective_implementation"] == "COLOCATED_LOGICAL_REFERENCE"
    ]

    archetype = {
        "CUSTOMER_AND_ADMIN": "SHARED_API_SERVICE",
        "CUSTOMER_ONLY": "CUSTOMER_API_SERVICE",
        "ADMIN_ONLY": "ADMIN_API_SERVICE",
        "INTERNAL_ONLY": "INTERNAL_PLATFORM_SERVICE",
    }[policy["exposure_policy"]]

    producer_required = bool(event_outgoing)
    consumer_required = bool(event_incoming)

    return {
        "planning_lesson": "129",
        "implementation_lesson": service["lesson_number"],
        "domain_id": service["domain_id"],
        "domain": service["domain"],
        "microservice_id": service["microservice_id"],
        "microservice_name": service_name,
        "service_archetype": archetype,
        "team_id": service["team_id"],
        "java_version": JAVA_VERSION,
        "spring_boot_version": SPRING_BOOT_VERSION,
        "build_tool": "Gradle",
        "gradle_version": GRADLE_VERSION,
        "build_dsl": "Kotlin",
        "packaging": "Executable JAR",
        "java_package": _java_package(service),
        "application_class": _application_class(service_name),
        "backend_module_path": service["backend_module_path"],
        "api_base_path": service["api_base_path"],
        "api_access_policy": policy["api_access_policy"],
        "customer_auth_audience": policy["customer_auth_audience"],
        "admin_auth_audience": policy["admin_auth_audience"],
        "web_stack": "Spring MVC",
        "api_contract": "REST + OpenAPI 3.1",
        "security_stack": ("Spring Security OAuth2 Resource Server"),
        "persistence_stack": "Spring Data JDBC",
        "database_engine": "PostgreSQL 18.6",
        "database_name": service["database_name"],
        "schema_name": service["schema_name"],
        "migration_tool": "Flyway",
        "owned_table_count": service["owned_table_count"],
        "full_cdc_table_count": service["full_cdc_table_count"],
        "excluded_cdc_table_count": service["excluded_cdc_table_count"],
        "outgoing_relationship_count": str(len(outgoing)),
        "incoming_relationship_count": str(len(incoming)),
        "event_outgoing_count": str(len(event_outgoing)),
        "event_incoming_count": str(len(event_incoming)),
        "colocated_validation_count": str(len(colocated)),
        "kafka_producer_required": ("Y" if producer_required else "N"),
        "kafka_consumer_required": ("Y" if consumer_required else "N"),
        "outbox_required": ("Y" if producer_required else "N"),
        "dlq_consumer_required": ("Y" if consumer_required else "N"),
        "resilience_stack": ("Resilience4j + idempotency + retry"),
        "observability_stack": ("Actuator + Micrometer + OpenTelemetry"),
        "testing_stack": (
            "JUnit 5 + Testcontainers + ArchUnit + Spring Cloud Contract"
        ),
        "container_strategy": ("OCI image + layered Spring Boot JAR"),
        "deployment_unit": service["deployment_unit"],
        "deployment_namespace": (f"retail-{service['domain']}"),
        "implementation_status": "PLANNED",
    }


def _validate_rows(
    rows: list[dict[str, str]],
) -> None:
    for row in rows:
        service = row["microservice_id"]

        if row["planning_lesson"] != "129":
            raise BackendContractError(f"{service} has an invalid planning lesson")

        implementation_lesson = int(row["implementation_lesson"])

        if not 201 <= implementation_lesson <= 1_200:
            raise BackendContractError(
                f"{service} has an invalid implementation lesson"
            )

        if row["java_version"] != JAVA_VERSION:
            raise BackendContractError(f"{service} has an invalid Java version")

        if row["spring_boot_version"] != (SPRING_BOOT_VERSION):
            raise BackendContractError(f"{service} has an invalid Spring Boot version")

        if int(row["owned_table_count"]) != 10:
            raise BackendContractError(f"{service} does not own 10 tables")

        cdc_total = int(row["full_cdc_table_count"]) + int(
            row["excluded_cdc_table_count"]
        )

        if cdc_total != 10:
            raise BackendContractError(f"{service} has invalid CDC totals")

        producer_required = int(row["event_outgoing_count"]) > 0

        consumer_required = int(row["event_incoming_count"]) > 0

        if row["kafka_producer_required"] != ("Y" if producer_required else "N"):
            raise BackendContractError(f"{service} has invalid producer configuration")

        if row["outbox_required"] != ("Y" if producer_required else "N"):
            raise BackendContractError(f"{service} has invalid outbox configuration")

        if row["kafka_consumer_required"] != ("Y" if consumer_required else "N"):
            raise BackendContractError(f"{service} has invalid consumer configuration")

        if row["dlq_consumer_required"] != ("Y" if consumer_required else "N"):
            raise BackendContractError(f"{service} has invalid DLQ configuration")

        if row["implementation_status"] != "PLANNED":
            raise BackendContractError(f"{service} has an invalid status")


def _java_package(
    service: dict[str, str],
) -> str:
    domain = service["domain"].replace("_", "")
    sequence = service["microservice_id"].split("-")[1]

    return f"com.agilearning.retail.{domain}.service{sequence}"


def _application_class(
    service_name: str,
) -> str:
    name = "".join(token.capitalize() for token in service_name.split("-"))

    return f"{name}Application"


def _require_unique(
    rows: list[dict[str, str]],
    column: str,
) -> None:
    values = {row[column] for row in rows}

    if len(values) != len(rows):
        raise BackendContractError(f"{column} values are not unique")


def _sum(
    rows: list[dict[str, str]],
    column: str,
) -> int:
    return sum(int(row[column]) for row in rows)


def _read_csv(
    path: Path,
) -> list[dict[str, str]]:
    with path.open(
        newline="",
        encoding="utf-8",
    ) as stream:
        return list(DictReader(stream))
