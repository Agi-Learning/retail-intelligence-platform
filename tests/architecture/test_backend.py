"""Tests for Spring Boot service implementation contracts."""

import csv
from pathlib import Path

from retail_intelligence_platform.architecture import (
    validate_backend_contract_manifest,
    write_backend_contract_manifest,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_GENERATED = _REPOSITORY_ROOT / "docs" / "architecture" / "generated"


def _generate_manifest(
    destination: Path,
) -> list[dict[str, str]]:
    count = write_backend_contract_manifest(
        _GENERATED / "microservice_implementation_manifest.csv",
        _GENERATED / "frontend_exposure_policy_manifest.csv",
        _GENERATED / "relationship_implementation_manifest.csv",
        destination,
    )

    assert count == 1_000
    validate_backend_contract_manifest(destination)

    with destination.open(
        newline="",
        encoding="utf-8",
    ) as stream:
        return list(csv.DictReader(stream))


def test_contract_covers_all_services(
    tmp_path: Path,
) -> None:
    rows = _generate_manifest(tmp_path / "backend.csv")

    assert len(rows) == 1_000
    assert len({row["microservice_id"] for row in rows}) == 1_000


def test_backend_archetype_distribution(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "backend.csv"
    _generate_manifest(destination)

    summary = validate_backend_contract_manifest(destination)

    assert summary.shared_api_services == 300
    assert summary.customer_api_services == 50
    assert summary.admin_api_services == 430
    assert summary.internal_platform_services == 220


def test_contract_preserves_table_security(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "backend.csv"
    _generate_manifest(destination)

    summary = validate_backend_contract_manifest(destination)

    assert summary.owned_tables == 10_000
    assert summary.full_cdc_tables == 9_802
    assert summary.excluded_cdc_tables == 198


def test_relationship_requirements_are_complete(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "backend.csv"
    _generate_manifest(destination)

    summary = validate_backend_contract_manifest(destination)

    assert summary.outgoing_relationships == 6_040
    assert summary.incoming_relationships == 6_040
    assert summary.event_producer_services == 990
    assert summary.event_consumer_services == 770
    assert summary.colocated_validator_services == 15


def test_backend_versions_and_paths_are_standardized(
    tmp_path: Path,
) -> None:
    rows = _generate_manifest(tmp_path / "backend.csv")

    assert all(row["java_version"] == "25" for row in rows)
    assert all(row["spring_boot_version"] == "4.1.1" for row in rows)
    assert len({row["backend_module_path"] for row in rows}) == 1_000
    assert len({row["java_package"] for row in rows}) == 1_000
