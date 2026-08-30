from pathlib import Path

from retail_intelligence_platform.architecture import (
    CdcMode,
    load_table_policies,
    summarize_table_policies,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

_ARCHITECTURE_PATH = (
    _REPOSITORY_ROOT
    / "docs"
    / "architecture"
    / "flipkart_scale_postgresql_10000_tables_with_relationships.csv"
)


def test_policy_accounts_for_every_table() -> None:
    policies = load_table_policies(_ARCHITECTURE_PATH)

    summary = summarize_table_policies(policies)

    assert summary.tables == 10_000
    assert summary.databases == 1_000
    assert summary.microservices == 1_000


def test_internal_tables_receive_full_cdc() -> None:
    policies = load_table_policies(_ARCHITECTURE_PATH)

    full_cdc = [
        policy for policy in policies if policy.effective_cdc_mode is CdcMode.FULL
    ]

    assert len(full_cdc) == 9_802
    assert all(policy.effective_kafka_topic for policy in full_cdc)


def test_restricted_tables_are_excluded() -> None:
    policies = load_table_policies(_ARCHITECTURE_PATH)

    restricted = [
        policy for policy in policies if policy.data_classification == "restricted"
    ]

    assert len(restricted) == 198

    for policy in restricted:
        assert policy.proposed_cdc_enabled
        assert policy.effective_cdc_mode is CdcMode.EXCLUDED
        assert policy.effective_kafka_topic is None
        assert policy.bronze_target is None
        assert policy.silver_target is None
        assert policy.gold_target is None


def test_effective_topic_count() -> None:
    policies = load_table_policies(_ARCHITECTURE_PATH)

    summary = summarize_table_policies(policies)

    assert summary.full_cdc == 9_802
    assert summary.excluded_cdc == 198
    assert summary.effective_topics == 9_802
