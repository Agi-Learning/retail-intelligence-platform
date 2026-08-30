import pytest

from retail_intelligence_platform.generator.loaders.events import (
    EventLoadResult,
    _validate_loaded_counts,
)
from retail_intelligence_platform.generator.profiles import (
    get_profile,
)


def valid_result() -> EventLoadResult:
    return EventLoadResult(
        outbox_events=300,
        published_events=290,
        pending_events=10,
        audit_events_attempted=400,
        audit_events_inserted=400,
    )


def test_event_result_total() -> None:
    assert valid_result().total_generated_rows == 700


def test_smoke_event_counts_are_valid() -> None:
    _validate_loaded_counts(
        valid_result(),
        get_profile("smoke"),
    )


def test_idempotent_audit_rerun_is_valid() -> None:
    result = valid_result()

    _validate_loaded_counts(
        EventLoadResult(
            outbox_events=result.outbox_events,
            published_events=result.published_events,
            pending_events=result.pending_events,
            audit_events_attempted=(result.audit_events_attempted),
            audit_events_inserted=0,
        ),
        get_profile("smoke"),
    )


def test_missing_outbox_events_are_rejected() -> None:
    result = valid_result()

    with pytest.raises(
        RuntimeError,
        match="outbox_events: expected 300",
    ):
        _validate_loaded_counts(
            EventLoadResult(
                outbox_events=299,
                published_events=result.published_events,
                pending_events=result.pending_events,
                audit_events_attempted=(result.audit_events_attempted),
                audit_events_inserted=(result.audit_events_inserted),
            ),
            get_profile("smoke"),
        )


def test_excessive_audit_insert_count_is_rejected() -> None:
    result = valid_result()

    with pytest.raises(
        RuntimeError,
        match="audit_events_inserted",
    ):
        _validate_loaded_counts(
            EventLoadResult(
                outbox_events=result.outbox_events,
                published_events=result.published_events,
                pending_events=result.pending_events,
                audit_events_attempted=(result.audit_events_attempted),
                audit_events_inserted=401,
            ),
            get_profile("smoke"),
        )
