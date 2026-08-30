from pathlib import Path

from retail_intelligence_platform.architecture import (
    validate_architecture,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

_TABLE_PATH = (
    _REPOSITORY_ROOT
    / "docs"
    / "architecture"
    / "flipkart_scale_postgresql_10000_tables_with_relationships.csv"
)

_RELATIONSHIP_PATH = (
    _REPOSITORY_ROOT
    / "docs"
    / "architecture"
    / "flipkart_scale_postgresql_db_relationships.csv"
)


def test_complete_architecture_registry() -> None:
    summary = validate_architecture(
        _TABLE_PATH,
        _RELATIONSHIP_PATH,
    )

    assert summary.domains == 100
    assert summary.microservices == 1_000
    assert summary.databases == 1_000
    assert summary.clusters == 800
    assert summary.tables == 10_000
    assert summary.topics == 10_000
    assert summary.relationships == 6_040


def test_table_class_distribution() -> None:
    summary = validate_architecture(
        _TABLE_PATH,
        _RELATIONSHIP_PATH,
    )

    assert summary.table_classes == {
        "transactional": 6_800,
        "reference": 900,
        "event": 1_300,
        "history": 1_000,
    }


def test_relationship_distribution() -> None:
    summary = validate_architecture(
        _TABLE_PATH,
        _RELATIONSHIP_PATH,
    )

    assert summary.relationship_types == {
        "PHYSICAL_FK": 18,
        "LOGICAL_REFERENCE": 6_022,
    }


def test_restricted_tables_require_policy_override() -> None:
    summary = validate_architecture(
        _TABLE_PATH,
        _RELATIONSHIP_PATH,
    )

    assert summary.restricted_tables == 198
    assert summary.restricted_cdc_requests == 198
