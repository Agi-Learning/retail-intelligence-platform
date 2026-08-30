from csv import DictReader
from pathlib import Path

from retail_intelligence_platform.architecture import (
    validate_service_manifest,
    write_service_manifest,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

_TABLE_MANIFEST_PATH = (
    _REPOSITORY_ROOT
    / "docs"
    / "architecture"
    / "generated"
    / "table_implementation_manifest.csv"
)


def _generate_service_manifest(
    destination: Path,
) -> list[dict[str, str]]:
    count = write_service_manifest(
        _TABLE_MANIFEST_PATH,
        destination,
    )

    assert count == 1_000

    validate_service_manifest(destination)

    with destination.open(
        encoding="utf-8",
        newline="",
    ) as source:
        return list(DictReader(source))


def test_manifest_contains_one_thousand_services(
    tmp_path: Path,
) -> None:
    rows = _generate_service_manifest(tmp_path / "services.csv")

    assert len(rows) == 1_000
    assert len({row["microservice_id"] for row in rows}) == 1_000


def test_each_service_owns_ten_tables(
    tmp_path: Path,
) -> None:
    rows = _generate_service_manifest(tmp_path / "services.csv")

    assert {int(row["owned_table_count"]) for row in rows} == {10}

    assert sum(int(row["owned_table_count"]) for row in rows) == 10_000


def test_each_service_has_at_least_one_database_cluster(
    tmp_path: Path,
) -> None:
    rows = _generate_service_manifest(tmp_path / "services.csv")

    assert all(int(row["db_cluster_count"]) >= 1 for row in rows)
    assert all(row["db_clusters"] for row in rows)


def test_each_service_has_unique_application_paths(
    tmp_path: Path,
) -> None:
    rows = _generate_service_manifest(tmp_path / "services.csv")

    assert len({row["backend_module_path"] for row in rows}) == 1_000

    assert len({row["api_base_path"] for row in rows}) == 1_000


def test_service_lessons_cover_201_through_1200(
    tmp_path: Path,
) -> None:
    rows = _generate_service_manifest(tmp_path / "services.csv")

    lessons = {int(row["lesson_number"]) for row in rows}

    assert lessons == set(range(201, 1_201))
