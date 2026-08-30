"""Generation of the enterprise relationship implementation manifest."""

from collections import Counter
from csv import DictReader, DictWriter
from dataclasses import dataclass
from pathlib import Path

EXPECTED_RELATIONSHIPS = 6_040
EXPECTED_DECLARED_PHYSICAL_FKS = 18
EXPECTED_LOGICAL_REFERENCES = 6_022

RELATIONSHIP_MANIFEST_COLUMNS = (
    "lesson_number",
    "relationship_id",
    "source_domain",
    "source_service",
    "source_cluster",
    "source_database",
    "source_schema",
    "source_table",
    "source_key",
    "source_full_table",
    "target_domain",
    "target_service",
    "target_cluster",
    "target_database",
    "target_schema",
    "target_table",
    "target_key",
    "target_full_table",
    "declared_relationship_type",
    "cardinality",
    "cross_cluster",
    "declared_consistency_model",
    "declared_sync_method",
    "source_of_truth",
    "event_topic",
    "on_missing_reference",
    "join_strategy",
    "effective_implementation",
    "enforcement_layer",
    "effective_sync_method",
    "kafka_required",
    "dlq_topic",
    "implementation_status",
    "description",
)


class RelationshipManifestError(ValueError):
    """Raised when a relationship manifest is inconsistent."""


@dataclass(frozen=True, slots=True)
class RelationshipManifestSummary:
    """Measurements from a validated relationship manifest."""

    relationships: int
    declared_physical_fks: int
    declared_logical_references: int
    postgresql_foreign_keys: int
    colocated_logical_references: int
    event_driven_logical_references: int
    kafka_integrations: int
    dlq_topics: int


def write_relationship_manifest(
    source: Path,
    destination: Path,
) -> int:
    """Write executable decisions for every declared relationship."""

    with source.open(
        newline="",
        encoding="utf-8",
    ) as stream:
        relationships = list(DictReader(stream))

    if len(relationships) != EXPECTED_RELATIONSHIPS:
        raise RelationshipManifestError(
            f"Expected {EXPECTED_RELATIONSHIPS} relationships, "
            f"found {len(relationships)}"
        )

    manifest_rows = [
        _build_manifest_row(relationship) for relationship in relationships
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
            fieldnames=list(RELATIONSHIP_MANIFEST_COLUMNS),
        )
        writer.writeheader()
        writer.writerows(manifest_rows)  # type: ignore[arg-type]

    return len(manifest_rows)


def validate_relationship_manifest(
    path: Path,
) -> RelationshipManifestSummary:
    """Validate completeness and executable relationship decisions."""

    with path.open(
        newline="",
        encoding="utf-8",
    ) as stream:
        reader = DictReader(stream)
        rows = list(reader)
        columns = tuple(reader.fieldnames or ())

    if columns != RELATIONSHIP_MANIFEST_COLUMNS:
        raise RelationshipManifestError("Unexpected relationship manifest columns")

    if len(rows) != EXPECTED_RELATIONSHIPS:
        raise RelationshipManifestError(
            f"Expected {EXPECTED_RELATIONSHIPS} rows, found {len(rows)}"
        )

    relationship_ids = {row["relationship_id"] for row in rows}

    if len(relationship_ids) != EXPECTED_RELATIONSHIPS:
        raise RelationshipManifestError("Relationship identifiers are not unique")

    declared_types = Counter(row["declared_relationship_type"] for row in rows)

    expected_declared_types = {
        "PHYSICAL_FK": EXPECTED_DECLARED_PHYSICAL_FKS,
        "LOGICAL_REFERENCE": EXPECTED_LOGICAL_REFERENCES,
    }

    if dict(declared_types) != expected_declared_types:
        raise RelationshipManifestError(
            f"Unexpected declared types: {dict(declared_types)}"
        )

    implementations = Counter(row["effective_implementation"] for row in rows)

    expected_implementations = {
        "COLOCATED_LOGICAL_REFERENCE": (EXPECTED_DECLARED_PHYSICAL_FKS),
        "EVENT_DRIVEN_LOGICAL_REFERENCE": (EXPECTED_LOGICAL_REFERENCES),
    }

    if dict(implementations) != expected_implementations:
        raise RelationshipManifestError(
            f"Unexpected effective implementations: {dict(implementations)}"
        )

    _validate_rows(rows)

    kafka_integrations = sum(row["kafka_required"] == "Y" for row in rows)

    dlq_topics = sum(bool(row["dlq_topic"]) for row in rows)

    return RelationshipManifestSummary(
        relationships=len(rows),
        declared_physical_fks=declared_types["PHYSICAL_FK"],
        declared_logical_references=declared_types["LOGICAL_REFERENCE"],
        postgresql_foreign_keys=implementations["POSTGRESQL_FOREIGN_KEY"],
        colocated_logical_references=implementations["COLOCATED_LOGICAL_REFERENCE"],
        event_driven_logical_references=implementations[
            "EVENT_DRIVEN_LOGICAL_REFERENCE"
        ],
        kafka_integrations=kafka_integrations,
        dlq_topics=dlq_topics,
    )


def _build_manifest_row(
    relationship: dict[str, str],
) -> dict[str, str]:
    declared_type = relationship["relationship_type"]

    same_database = relationship["source_database"] == relationship["target_database"]

    if declared_type == "PHYSICAL_FK" and same_database:
        effective_implementation = "POSTGRESQL_FOREIGN_KEY"
        enforcement_layer = "POSTGRESQL"
        effective_sync_method = "PostgreSQL foreign key"
        kafka_required = "N"
        dlq_topic = ""
    elif declared_type == "PHYSICAL_FK":
        effective_implementation = "COLOCATED_LOGICAL_REFERENCE"
        enforcement_layer = "APPLICATION_SERVICE"
        effective_sync_method = "Synchronous reference validation"
        kafka_required = "N"
        dlq_topic = ""
    else:
        effective_implementation = "EVENT_DRIVEN_LOGICAL_REFERENCE"
        enforcement_layer = "APPLICATION_AND_EVENT_CONSUMER"
        effective_sync_method = "Debezium CDC + Kafka projection"
        kafka_required = "Y"
        dlq_topic = f"{relationship['event_topic']}.dlq"

    return {
        "lesson_number": "126",
        "relationship_id": relationship["relationship_id"],
        "source_domain": relationship["source_domain"],
        "source_service": relationship["source_service"],
        "source_cluster": relationship["source_cluster"],
        "source_database": relationship["source_database"],
        "source_schema": relationship["source_schema"],
        "source_table": relationship["source_table"],
        "source_key": relationship["source_key"],
        "source_full_table": _full_table(
            relationship,
            side="source",
        ),
        "target_domain": relationship["target_domain"],
        "target_service": relationship["target_service"],
        "target_cluster": relationship["target_cluster"],
        "target_database": relationship["target_database"],
        "target_schema": relationship["target_schema"],
        "target_table": relationship["target_table"],
        "target_key": relationship["target_key"],
        "target_full_table": _full_table(
            relationship,
            side="target",
        ),
        "declared_relationship_type": declared_type,
        "cardinality": relationship["cardinality"],
        "cross_cluster": relationship["cross_cluster"],
        "declared_consistency_model": relationship["consistency_model"],
        "declared_sync_method": relationship["sync_method"],
        "source_of_truth": relationship["source_of_truth"],
        "event_topic": relationship["event_topic"],
        "on_missing_reference": relationship["on_missing_reference"],
        "join_strategy": relationship["join_strategy"],
        "effective_implementation": effective_implementation,
        "enforcement_layer": enforcement_layer,
        "effective_sync_method": effective_sync_method,
        "kafka_required": kafka_required,
        "dlq_topic": dlq_topic,
        "implementation_status": "PLANNED",
        "description": relationship["description"],
    }


def _validate_rows(
    rows: list[dict[str, str]],
) -> None:
    for row in rows:
        if row["lesson_number"] != "126":
            raise RelationshipManifestError(
                f"{row['relationship_id']} has an invalid lesson"
            )

        if not row["source_full_table"]:
            raise RelationshipManifestError(
                f"{row['relationship_id']} has no source endpoint"
            )

        if not row["target_full_table"]:
            raise RelationshipManifestError(
                f"{row['relationship_id']} has no target endpoint"
            )

        implementation = row["effective_implementation"]

        if (
            implementation == "POSTGRESQL_FOREIGN_KEY"
            and row["source_database"] != row["target_database"]
        ):
            raise RelationshipManifestError(
                f"{row['relationship_id']} attempts a "
                "cross-database PostgreSQL foreign key"
            )

        if implementation == "COLOCATED_LOGICAL_REFERENCE":
            if row["source_cluster"] != row["target_cluster"]:
                raise RelationshipManifestError(
                    f"{row['relationship_id']} is not colocated"
                )

            if row["source_database"] == row["target_database"]:
                raise RelationshipManifestError(
                    f"{row['relationship_id']} should use a PostgreSQL foreign key"
                )

        if implementation == "EVENT_DRIVEN_LOGICAL_REFERENCE":
            if row["kafka_required"] != "Y":
                raise RelationshipManifestError(
                    f"{row['relationship_id']} must use Kafka"
                )

            if not row["event_topic"] or not row["dlq_topic"]:
                raise RelationshipManifestError(
                    f"{row['relationship_id']} has incomplete Kafka routing"
                )

        if row["implementation_status"] != "PLANNED":
            raise RelationshipManifestError(
                f"{row['relationship_id']} has an invalid status"
            )


def _full_table(
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
