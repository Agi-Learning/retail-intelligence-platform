"""Validation of the enterprise application architecture registry."""

from collections import Counter
from csv import DictReader
from dataclasses import dataclass
from pathlib import Path

EXPECTED_DOMAINS = 100
EXPECTED_MICROSERVICES = 1_000
EXPECTED_DATABASES = 1_000
EXPECTED_CLUSTERS = 800
EXPECTED_TABLES = 10_000
EXPECTED_RELATIONSHIPS = 6_040
EXPECTED_TOPICS = 10_000
EXPECTED_RESTRICTED_TABLES = 198

EXPECTED_TABLE_CLASSES = {
    "transactional": 6_800,
    "reference": 900,
    "event": 1_300,
    "history": 1_000,
}

EXPECTED_RELATIONSHIP_TYPES = {
    "PHYSICAL_FK": 18,
    "LOGICAL_REFERENCE": 6_022,
}

REQUIRED_TABLE_COLUMNS = frozenset(
    {
        "domain_id",
        "domain",
        "service_group",
        "microservice_id",
        "microservice_name",
        "team_id",
        "db_cluster",
        "datastore",
        "database_name",
        "schema_name",
        "table_name",
        "full_table_name",
        "table_class",
        "cdc_enabled",
        "kafka_topic",
        "bronze_target",
        "silver_target",
        "gold_target",
        "purpose",
        "data_classification",
        "outgoing_relationship_count",
        "incoming_relationship_count",
    }
)

REQUIRED_RELATIONSHIP_COLUMNS = frozenset(
    {
        "relationship_id",
        "source_domain",
        "source_service",
        "source_cluster",
        "source_database",
        "source_schema",
        "source_table",
        "source_key",
        "target_domain",
        "target_service",
        "target_cluster",
        "target_database",
        "target_schema",
        "target_table",
        "target_key",
        "relationship_type",
        "cardinality",
        "cross_cluster",
        "consistency_model",
        "sync_method",
        "source_of_truth",
        "event_topic",
        "on_missing_reference",
        "join_strategy",
    }
)


class ArchitectureValidationError(ValueError):
    """Raised when an architecture document is inconsistent."""


@dataclass(frozen=True, slots=True)
class ArchitectureSummary:
    """Validated measurements from both architecture documents."""

    domains: int
    microservices: int
    databases: int
    clusters: int
    tables: int
    topics: int
    relationships: int
    restricted_tables: int
    restricted_cdc_requests: int
    table_classes: dict[str, int]
    relationship_types: dict[str, int]


def validate_architecture(
    table_path: Path,
    relationship_path: Path,
) -> ArchitectureSummary:
    """Validate tables, topics and cross-service relationships."""

    tables, table_columns = _read_csv(table_path)
    relationships, relationship_columns = _read_csv(relationship_path)

    _require_columns(
        table_columns,
        REQUIRED_TABLE_COLUMNS,
        document="table registry",
    )
    _require_columns(
        relationship_columns,
        REQUIRED_RELATIONSHIP_COLUMNS,
        document="relationship registry",
    )

    if len(tables) != EXPECTED_TABLES:
        raise ArchitectureValidationError(
            f"Expected {EXPECTED_TABLES} tables, found {len(tables)}"
        )

    if len(relationships) != EXPECTED_RELATIONSHIPS:
        raise ArchitectureValidationError(
            f"Expected {EXPECTED_RELATIONSHIPS} relationships, "
            f"found {len(relationships)}"
        )

    domains = _unique_values(tables, "domain")
    services = _unique_values(
        tables,
        "microservice_id",
    )
    databases = _unique_values(
        tables,
        "database_name",
    )
    clusters = _unique_values(tables, "db_cluster")
    full_names = _unique_values(
        tables,
        "full_table_name",
    )
    topics = _unique_values(tables, "kafka_topic")
    relationship_ids = _unique_values(
        relationships,
        "relationship_id",
    )

    _require_count("domains", domains, EXPECTED_DOMAINS)
    _require_count(
        "microservices",
        services,
        EXPECTED_MICROSERVICES,
    )
    _require_count(
        "databases",
        databases,
        EXPECTED_DATABASES,
    )
    _require_count(
        "clusters",
        clusters,
        EXPECTED_CLUSTERS,
    )
    _require_count(
        "unique tables",
        full_names,
        EXPECTED_TABLES,
    )
    _require_count(
        "unique topics",
        topics,
        EXPECTED_TOPICS,
    )
    _require_count(
        "unique relationships",
        relationship_ids,
        EXPECTED_RELATIONSHIPS,
    )

    table_classes = Counter(row["table_class"] for row in tables)

    if dict(table_classes) != EXPECTED_TABLE_CLASSES:
        raise ArchitectureValidationError(
            f"Unexpected table-class distribution: {dict(table_classes)}"
        )

    relationship_types = Counter(row["relationship_type"] for row in relationships)

    if dict(relationship_types) != EXPECTED_RELATIONSHIP_TYPES:
        raise ArchitectureValidationError(
            f"Unexpected relationship distribution: {dict(relationship_types)}"
        )

    restricted_tables = [
        row for row in tables if row["data_classification"] == "restricted"
    ]

    if len(restricted_tables) != EXPECTED_RESTRICTED_TABLES:
        raise ArchitectureValidationError(
            "Expected "
            f"{EXPECTED_RESTRICTED_TABLES} restricted tables, "
            f"found {len(restricted_tables)}"
        )

    restricted_cdc_requests = sum(
        row["cdc_enabled"] == "Y" for row in restricted_tables
    )

    _validate_relationship_endpoints(
        tables,
        relationships,
    )

    return ArchitectureSummary(
        domains=len(domains),
        microservices=len(services),
        databases=len(databases),
        clusters=len(clusters),
        tables=len(full_names),
        topics=len(topics),
        relationships=len(relationship_ids),
        restricted_tables=len(restricted_tables),
        restricted_cdc_requests=restricted_cdc_requests,
        table_classes=dict(table_classes),
        relationship_types=dict(relationship_types),
    )


def _validate_relationship_endpoints(
    tables: list[dict[str, str]],
    relationships: list[dict[str, str]],
) -> None:
    table_names = {row["full_table_name"] for row in tables}

    outgoing: Counter[str] = Counter()
    incoming: Counter[str] = Counter()

    for relationship in relationships:
        source = _relationship_endpoint(
            relationship,
            side="source",
        )
        target = _relationship_endpoint(
            relationship,
            side="target",
        )

        if source not in table_names:
            raise ArchitectureValidationError(f"Missing source table: {source}")

        if target not in table_names:
            raise ArchitectureValidationError(f"Missing target table: {target}")

        outgoing[source] += 1
        incoming[target] += 1

    for table in tables:
        full_name = table["full_table_name"]

        expected_outgoing = int(table["outgoing_relationship_count"])
        expected_incoming = int(table["incoming_relationship_count"])

        if outgoing[full_name] != expected_outgoing:
            raise ArchitectureValidationError(
                f"Outgoing relationship mismatch for "
                f"{full_name}: expected "
                f"{expected_outgoing}, found "
                f"{outgoing[full_name]}"
            )

        if incoming[full_name] != expected_incoming:
            raise ArchitectureValidationError(
                f"Incoming relationship mismatch for "
                f"{full_name}: expected "
                f"{expected_incoming}, found "
                f"{incoming[full_name]}"
            )


def _relationship_endpoint(
    relationship: dict[str, str],
    *,
    side: str,
) -> str:
    return ".".join(
        (
            relationship[f"{side}_database"],
            relationship[f"{side}_schema"],
            relationship[f"{side}_table"],
        )
    )


def _read_csv(
    path: Path,
) -> tuple[
    list[dict[str, str]],
    frozenset[str],
]:
    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as source:
        reader = DictReader(source)
        rows = list(reader)
        columns = frozenset(reader.fieldnames or ())

    return rows, columns


def _require_columns(
    actual: frozenset[str],
    required: frozenset[str],
    *,
    document: str,
) -> None:
    missing = required - actual

    if missing:
        raise ArchitectureValidationError(
            f"{document} is missing columns: {sorted(missing)}"
        )


def _unique_values(
    rows: list[dict[str, str]],
    column: str,
) -> set[str]:
    values = {row[column] for row in rows}

    if "" in values:
        raise ArchitectureValidationError(f"Blank value found in {column}")

    return values


def _require_count(
    label: str,
    values: set[str],
    expected: int,
) -> None:
    if len(values) != expected:
        raise ArchitectureValidationError(
            f"Expected {expected} {label}, found {len(values)}"
        )
