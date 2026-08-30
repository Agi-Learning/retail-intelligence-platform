from collections import Counter

from retail_intelligence_platform.generator.domains.events import (
    generate_audit_events,
    generate_outbox_events,
)
from retail_intelligence_platform.generator.profiles import (
    get_profile,
)


def test_smoke_event_counts() -> None:
    profile = get_profile("smoke")

    assert len(list(generate_outbox_events(profile))) == 300

    assert len(list(generate_audit_events(profile))) == 400


def test_event_generation_is_deterministic() -> None:
    profile = get_profile("smoke")

    assert list(generate_outbox_events(profile)) == list(
        generate_outbox_events(profile)
    )

    assert list(generate_audit_events(profile)) == list(generate_audit_events(profile))


def test_outbox_event_ids_are_unique() -> None:
    profile = get_profile("small")
    events = list(generate_outbox_events(profile))

    assert len({event.event_id for event in events}) == len(events)


def test_outbox_publication_constraints() -> None:
    profile = get_profile("small")

    for event in generate_outbox_events(profile):
        assert event.event_version > 0
        assert isinstance(event.payload, dict)
        assert isinstance(event.headers, dict)
        assert event.created_at >= event.occurred_at
        assert event.retry_count >= 0

        if event.status == "PUBLISHED":
            assert event.published_at is not None
            assert event.published_at >= event.occurred_at
        else:
            assert event.published_at is None


def test_outbox_has_published_and_pending_events() -> None:
    profile = get_profile("smoke")

    statuses = Counter(event.status for event in generate_outbox_events(profile))

    assert statuses == {
        "PUBLISHED": 290,
        "PENDING": 10,
    }


def test_audit_events_contain_no_secret_fields() -> None:
    profile = get_profile("small")

    prohibited_terms = {
        "password",
        "token",
        "secret",
        "cvv",
        "card_number",
        "private_key",
    }

    for event in generate_audit_events(profile):
        detail_keys = {key.lower() for key in event.details}

        assert detail_keys.isdisjoint(prohibited_terms)


def test_audit_fields_respect_constraints() -> None:
    profile = get_profile("small")

    for event in generate_audit_events(profile):
        assert event.actor_type.strip()
        assert event.action.strip()
        assert event.entity_type.strip()
        assert event.entity_id.strip()
        assert isinstance(event.details, dict)
        assert event.source_ip is not None
        assert event.source_ip.startswith("198.51.100.")


def test_audit_event_keys_are_unique_and_deterministic() -> None:
    profile = get_profile("smoke")

    first_run = list(generate_audit_events(profile))
    second_run = list(generate_audit_events(profile))

    first_keys = [record.event_key for record in first_run]
    second_keys = [record.event_key for record in second_run]

    assert len(first_keys) == len(first_run)
    assert len(set(first_keys)) == len(first_keys)
    assert first_keys == second_keys
