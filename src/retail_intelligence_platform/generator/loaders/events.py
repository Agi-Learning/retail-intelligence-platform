"""Transactional loading for Outbox and append-only audit events."""

from collections.abc import Iterable
from dataclasses import dataclass

import psycopg
from psycopg.types.json import Jsonb

from retail_intelligence_platform.generator.config import (
    GeneratorSettings,
)
from retail_intelligence_platform.generator.domains.events import (
    AuditEventRecord,
    OutboxEventRecord,
    generate_audit_events,
    generate_outbox_events,
)
from retail_intelligence_platform.generator.loaders.catalog import (
    batched,
)
from retail_intelligence_platform.generator.profiles import (
    GenerationProfile,
)


@dataclass(frozen=True, slots=True)
class EventLoadResult:
    outbox_events: int
    published_events: int
    pending_events: int
    audit_events_attempted: int
    audit_events_inserted: int

    @property
    def total_generated_rows(self) -> int:
        return self.outbox_events + self.audit_events_attempted


def load_events(
    settings: GeneratorSettings,
    profile: GenerationProfile,
) -> EventLoadResult:
    """Load Outbox and audit events in one transaction."""

    password = settings.load_password()

    with (
        psycopg.connect(
            host=settings.host,
            port=settings.port,
            dbname=settings.database,
            user=settings.user,
            password=password.get_secret_value(),
            connect_timeout=settings.connect_timeout_seconds,
            application_name="retail-event-loader",
        ) as connection,
        connection.cursor() as cursor,
    ):
        _load_outbox_events(
            cursor,
            generate_outbox_events(profile),
            settings.batch_size,
        )

        audit_inserted = _load_audit_events(
            cursor,
            generate_audit_events(profile),
            settings.batch_size,
        )

        result = _read_result(
            cursor,
            profile,
            audit_inserted,
        )

        _validate_loaded_counts(
            result,
            profile,
        )

        connection.commit()

    return result


def _load_outbox_events(
    cursor: psycopg.Cursor,
    records: Iterable[OutboxEventRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO outbox.events (
            event_id,
            aggregate_type,
            aggregate_id,
            event_type,
            event_version,
            payload,
            headers,
            status,
            occurred_at,
            created_at,
            published_at,
            retry_count,
            last_error
        )
        VALUES (
            %(event_id)s,
            %(aggregate_type)s,
            %(aggregate_id)s,
            %(event_type)s,
            %(event_version)s,
            %(payload)s,
            %(headers)s,
            %(status)s,
            %(occurred_at)s,
            %(created_at)s,
            %(published_at)s,
            %(retry_count)s,
            %(last_error)s
        )
        ON CONFLICT (event_id)
        DO NOTHING;
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "event_id": record.event_id,
                    "aggregate_type": record.aggregate_type,
                    "aggregate_id": record.aggregate_id,
                    "event_type": record.event_type,
                    "event_version": record.event_version,
                    "payload": Jsonb(record.payload),
                    "headers": Jsonb(record.headers),
                    "status": record.status,
                    "occurred_at": record.occurred_at,
                    "created_at": record.created_at,
                    "published_at": record.published_at,
                    "retry_count": record.retry_count,
                    "last_error": record.last_error,
                }
                for record in batch
            ],
        )


def _load_audit_events(
    cursor: psycopg.Cursor,
    records: Iterable[AuditEventRecord],
    batch_size: int,
) -> int:
    statement = """
        INSERT INTO audit.audit_events (
            event_key,
            actor_type,
            actor_id,
            action,
            entity_type,
            entity_id,
            source_ip,
            correlation_id,
            details,
            occurred_at
        )
        VALUES (
            %(event_key)s,
            %(actor_type)s,
            %(actor_id)s,
            %(action)s,
            %(entity_type)s,
            %(entity_id)s,
            %(source_ip)s,
            %(correlation_id)s,
            %(details)s,
            %(occurred_at)s
        )
        ON CONFLICT
        DO NOTHING;
    """

    inserted = 0

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "event_key": record.event_key,
                    "actor_type": record.actor_type,
                    "actor_id": record.actor_id,
                    "action": record.action,
                    "entity_type": record.entity_type,
                    "entity_id": record.entity_id,
                    "source_ip": record.source_ip,
                    "correlation_id": record.correlation_id,
                    "details": Jsonb(record.details),
                    "occurred_at": record.occurred_at,
                }
                for record in batch
            ],
        )

        if cursor.rowcount > 0:
            inserted += cursor.rowcount

    return inserted


def _read_result(
    cursor: psycopg.Cursor,
    profile: GenerationProfile,
    audit_inserted: int,
) -> EventLoadResult:
    cursor.execute(
        """
        SELECT
            count(*),
            count(*) FILTER (
                WHERE status = 'PUBLISHED'
            ),
            count(*) FILTER (
                WHERE status = 'PENDING'
            )
        FROM outbox.events
        WHERE headers ->> 'event_source' =
            'synthetic-generator';
        """
    )

    row = cursor.fetchone()

    if row is None:
        raise RuntimeError("Outbox count query returned no result")

    return EventLoadResult(
        outbox_events=row[0],
        published_events=row[1],
        pending_events=row[2],
        audit_events_attempted=profile.order_count * 4,
        audit_events_inserted=audit_inserted,
    )


def _validate_loaded_counts(
    result: EventLoadResult,
    profile: GenerationProfile,
) -> None:
    expected_outbox = profile.order_count * 3
    expected_audit = profile.order_count * 4
    expected_pending = profile.order_count // 10
    expected_published = expected_outbox - expected_pending

    expected = {
        "outbox_events": expected_outbox,
        "published_events": expected_published,
        "pending_events": expected_pending,
        "audit_events_attempted": expected_audit,
    }

    actual = {
        "outbox_events": result.outbox_events,
        "published_events": result.published_events,
        "pending_events": result.pending_events,
        "audit_events_attempted": result.audit_events_attempted,
    }

    errors = [
        f"{name}: expected {expected[name]}, found {actual[name]}"
        for name in expected
        if actual[name] != expected[name]
    ]

    if not 0 <= result.audit_events_inserted <= expected_audit:
        errors.append(f"audit_events_inserted must be between 0 and {expected_audit}")

    if errors:
        raise RuntimeError("Event validation failed:\n- " + "\n- ".join(errors))
