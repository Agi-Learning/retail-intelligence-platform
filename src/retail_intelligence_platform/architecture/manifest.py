"""Generation of the enterprise table implementation manifest."""

from csv import DictReader, DictWriter
from pathlib import Path

from retail_intelligence_platform.architecture.policy import (
    CdcMode,
    load_table_policies,
)

MANIFEST_COLUMNS = (
    "lesson_number",
    "domain_id",
    "domain",
    "service_group",
    "microservice_id",
    "microservice_name",
    "team_id",
    "db_cluster",
    "database_name",
    "schema_name",
    "table_name",
    "full_table_name",
    "table_class",
    "data_classification",
    "storage_role",
    "target_postgres_version",
    "connector_scope",
    "replication_slot_strategy",
    "proposed_cdc_enabled",
    "effective_cdc_mode",
    "proposed_kafka_topic",
    "effective_kafka_topic",
    "bronze_target",
    "silver_target",
    "gold_target",
    "implementation_status",
    "policy_reason",
)


def write_implementation_manifest(
    architecture_path: Path,
    destination_path: Path,
) -> int:
    """Write one effective implementation row per source table."""

    policies = load_table_policies(architecture_path)

    policies_by_name = {policy.full_table_name: policy for policy in policies}

    with architecture_path.open(
        encoding="utf-8-sig",
        newline="",
    ) as source:
        source_rows = list(DictReader(source))

    manifest_rows = []

    for source_row in source_rows:
        full_name = source_row["full_table_name"]
        policy = policies_by_name[full_name]

        service_number = int(source_row["microservice_id"].removeprefix("svc-"))

        manifest_rows.append(
            {
                "lesson_number": str(200 + service_number),
                "domain_id": source_row["domain_id"],
                "domain": source_row["domain"],
                "service_group": source_row["service_group"],
                "microservice_id": source_row["microservice_id"],
                "microservice_name": source_row["microservice_name"],
                "team_id": source_row["team_id"],
                "db_cluster": source_row["db_cluster"],
                "database_name": source_row["database_name"],
                "schema_name": source_row["schema_name"],
                "table_name": source_row["table_name"],
                "full_table_name": full_name,
                "table_class": source_row["table_class"],
                "data_classification": source_row["data_classification"],
                "storage_role": ("POSTGRESQL_OPERATIONAL"),
                "target_postgres_version": "18.6",
                "connector_scope": "DATABASE",
                "replication_slot_strategy": ("ONE_PER_DATABASE"),
                "proposed_cdc_enabled": source_row["cdc_enabled"],
                "effective_cdc_mode": (policy.effective_cdc_mode.value),
                "proposed_kafka_topic": (policy.proposed_kafka_topic),
                "effective_kafka_topic": (policy.effective_kafka_topic or ""),
                "bronze_target": (policy.bronze_target or ""),
                "silver_target": (policy.silver_target or ""),
                "gold_target": (policy.gold_target or ""),
                "implementation_status": "PLANNED",
                "policy_reason": policy.policy_reason,
            }
        )

    manifest_rows.sort(
        key=lambda row: (
            int(row["lesson_number"]),
            row["full_table_name"],
        )
    )

    destination_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with destination_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as destination:
        writer = DictWriter(
            destination,
            fieldnames=MANIFEST_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    return len(manifest_rows)


def validate_implementation_manifest(
    manifest_path: Path,
) -> None:
    """Validate coverage and effective security controls."""

    with manifest_path.open(
        encoding="utf-8",
        newline="",
    ) as source:
        reader = DictReader(source)
        rows = list(reader)
        columns = tuple(reader.fieldnames or ())

    if columns != MANIFEST_COLUMNS:
        raise ValueError("Unexpected implementation manifest columns")

    if len(rows) != 10_000:
        raise ValueError(f"Expected 10000 manifest rows, found {len(rows)}")

    full_names = {row["full_table_name"] for row in rows}

    if len(full_names) != 10_000:
        raise ValueError("Implementation manifest contains duplicate table names")

    lesson_numbers = {int(row["lesson_number"]) for row in rows}

    if lesson_numbers != set(range(201, 1_201)):
        raise ValueError("Implementation lessons do not cover 201 through 1200")

    per_lesson: dict[int, int] = {}

    for row in rows:
        lesson_number = int(row["lesson_number"])
        per_lesson[lesson_number] = (
            per_lesson.get(
                lesson_number,
                0,
            )
            + 1
        )

        mode = CdcMode(row["effective_cdc_mode"])

        if row["data_classification"] == "restricted" and mode is not CdcMode.EXCLUDED:
            raise ValueError(f"Restricted table enables CDC: {row['full_table_name']}")

        if mode is CdcMode.EXCLUDED and any(
            row[column]
            for column in (
                "effective_kafka_topic",
                "bronze_target",
                "silver_target",
                "gold_target",
            )
        ):
            raise ValueError(
                f"Excluded table has downstream targets: {row['full_table_name']}"
            )

    if set(per_lesson.values()) != {10}:
        raise ValueError("Every microservice lesson must contain exactly ten tables")
