"""Tests for the enterprise domain implementation manifest."""

import csv
from pathlib import Path

from retail_intelligence_platform.architecture import (
    validate_domain_manifest,
    write_domain_manifest,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_GENERATED = _REPOSITORY_ROOT / "docs" / "architecture" / "generated"

_SERVICE_MANIFEST = _GENERATED / "microservice_implementation_manifest.csv"

_RELATIONSHIP_MANIFEST = _GENERATED / "relationship_implementation_manifest.csv"


def _generate_manifest(
    destination: Path,
) -> list[dict[str, str]]:
    count = write_domain_manifest(
        _SERVICE_MANIFEST,
        _RELATIONSHIP_MANIFEST,
        destination,
    )

    assert count == 100
    validate_domain_manifest(destination)

    with destination.open(
        newline="",
        encoding="utf-8",
    ) as stream:
        return list(csv.DictReader(stream))


def test_manifest_contains_one_hundred_domains(
    tmp_path: Path,
) -> None:
    rows = _generate_manifest(tmp_path / "domains.csv")

    assert len(rows) == 100
    assert len({row["domain"] for row in rows}) == 100


def test_each_domain_owns_expected_resources(
    tmp_path: Path,
) -> None:
    rows = _generate_manifest(tmp_path / "domains.csv")

    assert all(row["service_count"] == "10" for row in rows)
    assert all(row["database_count"] == "10" for row in rows)
    assert all(row["table_count"] == "100" for row in rows)


def test_domain_totals_cover_complete_architecture(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "domains.csv"
    _generate_manifest(destination)

    summary = validate_domain_manifest(destination)

    assert summary.services == 1_000
    assert summary.databases == 1_000
    assert summary.tables == 10_000
    assert summary.outgoing_relationships == 6_040
    assert summary.incoming_relationships == 6_040


def test_domain_relationship_implementations_reconcile(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "domains.csv"
    _generate_manifest(destination)

    summary = validate_domain_manifest(destination)

    assert summary.colocated_logical_references == 18
    assert summary.event_driven_references == 6_022


def test_frontend_policy_is_explicitly_pending(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "domains.csv"
    _generate_manifest(destination)

    summary = validate_domain_manifest(destination)

    assert summary.frontend_policies_pending == 100
