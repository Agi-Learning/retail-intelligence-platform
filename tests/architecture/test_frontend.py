"""Tests for deterministic frontend exposure policies."""

import csv
from pathlib import Path

from retail_intelligence_platform.architecture import (
    validate_frontend_policy_manifest,
    write_frontend_policy_manifest,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_GENERATED = _REPOSITORY_ROOT / "docs" / "architecture" / "generated"

_DOMAIN_MANIFEST = _GENERATED / "domain_implementation_manifest.csv"


def _generate_manifest(
    destination: Path,
) -> list[dict[str, str]]:
    count = write_frontend_policy_manifest(
        _DOMAIN_MANIFEST,
        destination,
    )

    assert count == 100
    validate_frontend_policy_manifest(destination)

    with destination.open(
        newline="",
        encoding="utf-8",
    ) as stream:
        return list(csv.DictReader(stream))


def test_policy_covers_all_domains(
    tmp_path: Path,
) -> None:
    rows = _generate_manifest(tmp_path / "frontend.csv")

    assert len(rows) == 100
    assert len({row["domain"] for row in rows}) == 100


def test_exposure_policy_distribution(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "frontend.csv"
    _generate_manifest(destination)

    summary = validate_frontend_policy_manifest(destination)

    assert summary.customer_and_admin == 30
    assert summary.customer_only == 5
    assert summary.admin_only == 43
    assert summary.internal_only == 22


def test_customer_and_admin_coverage(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "frontend.csv"
    _generate_manifest(destination)

    summary = validate_frontend_policy_manifest(destination)

    assert summary.customer_web_domains == 35
    assert summary.admin_web_domains == 73


def test_api_access_policy_distribution(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "frontend.csv"
    _generate_manifest(destination)

    summary = validate_frontend_policy_manifest(destination)

    assert summary.public_api_domains == 35
    assert summary.internal_api_domains == 65


def test_internal_domains_have_no_browser_routes(
    tmp_path: Path,
) -> None:
    rows = _generate_manifest(tmp_path / "frontend.csv")

    internal = [row for row in rows if row["exposure_policy"] == "INTERNAL_ONLY"]

    assert len(internal) == 22
    assert all(not row["customer_route"] for row in internal)
    assert all(not row["admin_route"] for row in internal)
