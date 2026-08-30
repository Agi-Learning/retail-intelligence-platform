"""Tests for the relationship implementation manifest."""

import csv
from pathlib import Path

from retail_intelligence_platform.architecture import (
    validate_relationship_manifest,
    write_relationship_manifest,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

_SOURCE = (
    _REPOSITORY_ROOT
    / "docs"
    / "architecture"
    / "flipkart_scale_postgresql_db_relationships.csv"
)


def _generate_manifest(
    destination: Path,
) -> list[dict[str, str]]:
    count = write_relationship_manifest(
        _SOURCE,
        destination,
    )

    assert count == 6_040

    validate_relationship_manifest(destination)

    with destination.open(
        newline="",
        encoding="utf-8",
    ) as stream:
        return list(csv.DictReader(stream))


def test_manifest_contains_every_relationship(
    tmp_path: Path,
) -> None:
    rows = _generate_manifest(tmp_path / "relationships.csv")

    assert len(rows) == 6_040
    assert len({row["relationship_id"] for row in rows}) == 6_040


def test_declared_relationship_distribution(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "relationships.csv"
    _generate_manifest(destination)

    summary = validate_relationship_manifest(destination)

    assert summary.declared_physical_fks == 18
    assert summary.declared_logical_references == 6_022


def test_cross_database_fks_are_corrected(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "relationships.csv"
    _generate_manifest(destination)

    summary = validate_relationship_manifest(destination)

    assert summary.postgresql_foreign_keys == 0
    assert summary.colocated_logical_references == 18


def test_event_driven_relationships_use_kafka(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "relationships.csv"
    _generate_manifest(destination)

    summary = validate_relationship_manifest(destination)

    assert summary.event_driven_logical_references == 6_022
    assert summary.kafka_integrations == 6_022
    assert summary.dlq_topics == 6_022


def test_manifest_preserves_all_endpoints(
    tmp_path: Path,
) -> None:
    rows = _generate_manifest(tmp_path / "relationships.csv")

    assert all(row["source_full_table"] for row in rows)
    assert all(row["target_full_table"] for row in rows)
    assert all(row["implementation_status"] == "PLANNED" for row in rows)
