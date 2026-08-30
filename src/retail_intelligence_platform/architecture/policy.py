"""Secure implementation policy derived from the source registry."""

from collections import Counter
from csv import DictReader
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

EXPECTED_POLICY_COUNT = 10_000
EXPECTED_FULL_CDC_COUNT = 9_802
EXPECTED_EXCLUDED_CDC_COUNT = 198


class CdcMode(StrEnum):
    """Effective CDC handling for an operational table."""

    FULL = "FULL"
    EXCLUDED = "EXCLUDED"


@dataclass(frozen=True, slots=True)
class TablePolicy:
    """Effective implementation policy for one table."""

    full_table_name: str
    domain: str
    microservice_id: str
    database_name: str
    table_class: str
    data_classification: str
    proposed_cdc_enabled: bool
    proposed_kafka_topic: str
    effective_cdc_mode: CdcMode
    effective_kafka_topic: str | None
    bronze_target: str | None
    silver_target: str | None
    gold_target: str | None
    policy_reason: str


@dataclass(frozen=True, slots=True)
class PolicySummary:
    """Measurements for the complete derived policy."""

    tables: int
    full_cdc: int
    excluded_cdc: int
    effective_topics: int
    databases: int
    microservices: int


def load_table_policies(
    architecture_path: Path,
) -> tuple[TablePolicy, ...]:
    """Load the source registry and derive secure policies."""

    with architecture_path.open(
        encoding="utf-8-sig",
        newline="",
    ) as source:
        rows = list(DictReader(source))

    policies = tuple(_derive_policy(row) for row in rows)

    validate_table_policies(policies)

    return policies


def summarize_table_policies(
    policies: tuple[TablePolicy, ...],
) -> PolicySummary:
    """Summarize an already validated policy collection."""

    validate_table_policies(policies)

    mode_counts = Counter(policy.effective_cdc_mode for policy in policies)

    topics = {
        policy.effective_kafka_topic
        for policy in policies
        if policy.effective_kafka_topic is not None
    }

    return PolicySummary(
        tables=len(policies),
        full_cdc=mode_counts[CdcMode.FULL],
        excluded_cdc=mode_counts[CdcMode.EXCLUDED],
        effective_topics=len(topics),
        databases=len({policy.database_name for policy in policies}),
        microservices=len({policy.microservice_id for policy in policies}),
    )


def validate_table_policies(
    policies: tuple[TablePolicy, ...],
) -> None:
    """Validate coverage and security invariants."""

    if len(policies) != EXPECTED_POLICY_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_POLICY_COUNT} policies, found {len(policies)}"
        )

    full_names = {policy.full_table_name for policy in policies}

    if len(full_names) != EXPECTED_POLICY_COUNT:
        raise ValueError("Table policies contain duplicate names")

    mode_counts = Counter(policy.effective_cdc_mode for policy in policies)

    if mode_counts[CdcMode.FULL] != EXPECTED_FULL_CDC_COUNT:
        raise ValueError(
            f"Unexpected FULL CDC policy count: {mode_counts[CdcMode.FULL]}"
        )

    if mode_counts[CdcMode.EXCLUDED] != EXPECTED_EXCLUDED_CDC_COUNT:
        raise ValueError(
            f"Unexpected EXCLUDED CDC policy count: {mode_counts[CdcMode.EXCLUDED]}"
        )

    for policy in policies:
        if (
            policy.data_classification == "restricted"
            and policy.effective_cdc_mode is not CdcMode.EXCLUDED
        ):
            raise ValueError(
                f"Restricted table incorrectly enables CDC: {policy.full_table_name}"
            )

        if policy.effective_cdc_mode is CdcMode.EXCLUDED and any(
            target is not None
            for target in (
                policy.effective_kafka_topic,
                policy.bronze_target,
                policy.silver_target,
                policy.gold_target,
            )
        ):
            raise ValueError(
                "Excluded table has an effective "
                "downstream target: "
                f"{policy.full_table_name}"
            )

    effective_topics = [
        policy.effective_kafka_topic
        for policy in policies
        if policy.effective_kafka_topic is not None
    ]

    if len(effective_topics) != len(set(effective_topics)):
        raise ValueError("Effective Kafka topics are not unique")


def _derive_policy(
    row: dict[str, str],
) -> TablePolicy:
    restricted = row["data_classification"] == "restricted"

    if restricted:
        return TablePolicy(
            full_table_name=row["full_table_name"],
            domain=row["domain"],
            microservice_id=row["microservice_id"],
            database_name=row["database_name"],
            table_class=row["table_class"],
            data_classification=row["data_classification"],
            proposed_cdc_enabled=(row["cdc_enabled"] == "Y"),
            proposed_kafka_topic=row["kafka_topic"],
            effective_cdc_mode=CdcMode.EXCLUDED,
            effective_kafka_topic=None,
            bronze_target=None,
            silver_target=None,
            gold_target=None,
            policy_reason=(
                "Restricted source table; raw CDC "
                "and downstream publication are disabled."
            ),
        )

    return TablePolicy(
        full_table_name=row["full_table_name"],
        domain=row["domain"],
        microservice_id=row["microservice_id"],
        database_name=row["database_name"],
        table_class=row["table_class"],
        data_classification=row["data_classification"],
        proposed_cdc_enabled=(row["cdc_enabled"] == "Y"),
        proposed_kafka_topic=row["kafka_topic"],
        effective_cdc_mode=CdcMode.FULL,
        effective_kafka_topic=row["kafka_topic"],
        bronze_target=row["bronze_target"],
        silver_target=row["silver_target"],
        gold_target=row["gold_target"],
        policy_reason=("Internal table approved for full CDC."),
    )
