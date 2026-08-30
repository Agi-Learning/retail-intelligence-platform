from csv import DictReader
from pathlib import Path

from retail_intelligence_platform.architecture import (
    validate_implementation_manifest,
    write_implementation_manifest,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

_ARCHITECTURE_PATH = (
    _REPOSITORY_ROOT
    / "docs"
    / "architecture"
    / "flipkart_scale_postgresql_10000_tables_with_relationships.csv"
)


def _generate_manifest(
    destination: Path,
) -> list[dict[str, str]]:
    rows_written = write_implementation_manifest(
        _ARCHITECTURE_PATH,
        destination,
    )

    assert rows_written == 10_000

    validate_implementation_manifest(destination)

    with destination.open(
        encoding="utf-8",
        newline="",
    ) as source:
        return list(DictReader(source))


def test_manifest_contains_every_table(
    tmp_path: Path,
) -> None:
    rows = _generate_manifest(tmp_path / "manifest.csv")

    assert len(rows) == 10_000
    assert len({row["full_table_name"] for row in rows}) == 10_000


def test_manifest_assigns_ten_tables_per_lesson(
    tmp_path: Path,
) -> None:
    rows = _generate_manifest(tmp_path / "manifest.csv")

    lesson_counts: dict[str, int] = {}

    for row in rows:
        lesson = row["lesson_number"]
        lesson_counts[lesson] = lesson_counts.get(lesson, 0) + 1

    assert len(lesson_counts) == 1_000
    assert set(lesson_counts.values()) == {10}
    assert min(map(int, lesson_counts)) == 201
    assert max(map(int, lesson_counts)) == 1_200


def test_manifest_applies_secure_cdc_policy(
    tmp_path: Path,
) -> None:
    rows = _generate_manifest(tmp_path / "manifest.csv")

    modes: dict[str, int] = {}

    for row in rows:
        mode = row["effective_cdc_mode"]
        modes[mode] = modes.get(mode, 0) + 1

    assert modes == {
        "FULL": 9_802,
        "EXCLUDED": 198,
    }


def test_manifest_uses_current_postgresql_version(
    tmp_path: Path,
) -> None:
    rows = _generate_manifest(tmp_path / "manifest.csv")

    assert {row["target_postgres_version"] for row in rows} == {"18.6"}

    assert {row["replication_slot_strategy"] for row in rows} == {"ONE_PER_DATABASE"}
