/*
=========================================================
Retail Intelligence Platform
Migration: V010
Purpose:
  - Create the transactional Outbox
  - Persist domain events atomically with business changes
  - Support Debezium CDC and polling publishers
  - Track publication, retries and terminal failures
=========================================================
*/

SET ROLE retail_owner;

CREATE TABLE outbox.events (
    event_id UUID
        NOT NULL
        DEFAULT gen_random_uuid(),

    aggregate_type VARCHAR(100)
        NOT NULL,

    aggregate_id VARCHAR(100)
        NOT NULL,

    event_type VARCHAR(150)
        NOT NULL,

    event_version INTEGER
        NOT NULL
        DEFAULT 1,

    payload JSONB
        NOT NULL,

    headers JSONB,

    status outbox.event_status
        NOT NULL
        DEFAULT 'PENDING',

    occurred_at TIMESTAMPTZ
        NOT NULL,

    created_at TIMESTAMPTZ
        NOT NULL
        DEFAULT clock_timestamp(),

    published_at TIMESTAMPTZ,

    retry_count INTEGER
        NOT NULL
        DEFAULT 0,

    last_error TEXT,

    CONSTRAINT pk_outbox_events
        PRIMARY KEY (event_id),

    CONSTRAINT ck_outbox_aggregate_type
        CHECK (char_length(btrim(aggregate_type)) > 0),

    CONSTRAINT ck_outbox_aggregate_id
        CHECK (char_length(btrim(aggregate_id)) > 0),

    CONSTRAINT ck_outbox_event_type
        CHECK (char_length(btrim(event_type)) > 0),

    CONSTRAINT ck_outbox_event_version_positive
        CHECK (event_version > 0),

    CONSTRAINT ck_outbox_payload_object
        CHECK (jsonb_typeof(payload) = 'object'),

    CONSTRAINT ck_outbox_headers_object
        CHECK (
            headers IS NULL
            OR jsonb_typeof(headers) = 'object'
        ),

    CONSTRAINT ck_outbox_created_after_occurrence
        CHECK (created_at >= occurred_at),

    CONSTRAINT ck_outbox_publication_time
        CHECK (
            published_at IS NULL
            OR published_at >= occurred_at
        ),

    CONSTRAINT ck_outbox_publication_status
        CHECK (
            (
                status = 'PUBLISHED'
                AND published_at IS NOT NULL
            )
            OR
            (
                status <> 'PUBLISHED'
                AND published_at IS NULL
            )
        ),

    CONSTRAINT ck_outbox_retry_nonnegative
        CHECK (retry_count >= 0),

    CONSTRAINT ck_outbox_last_error
        CHECK (
            last_error IS NULL
            OR char_length(btrim(last_error)) > 0
        )
);

COMMENT ON TABLE outbox.events IS
    'Domain events written in the same transaction as their originating business changes.';

COMMENT ON COLUMN outbox.events.aggregate_type IS
    'Business aggregate category, such as Order, Payment or InventoryReservation.';

COMMENT ON COLUMN outbox.events.aggregate_id IS
    'Stable business identifier of the aggregate that produced the event.';

COMMENT ON COLUMN outbox.events.event_type IS
    'Version-independent event name, such as OrderCreated or PaymentSucceeded.';

COMMENT ON COLUMN outbox.events.event_version IS
    'Schema version of the event payload.';

COMMENT ON COLUMN outbox.events.headers IS
    'Optional metadata such as correlation ID, causation ID and trace context.';

/*
Supports ordered event-stream reconstruction for one aggregate.
*/

CREATE INDEX idx_outbox_aggregate
    ON outbox.events (
        aggregate_type,
        aggregate_id,
        occurred_at,
        event_id
    );

/*
Supports a polling publisher selecting publishable events.

FAILED events remain eligible for controlled retries.
DEAD events require manual investigation.
*/

CREATE INDEX idx_outbox_pending
    ON outbox.events (
        status,
        created_at,
        event_id
    )
    WHERE status IN ('PENDING', 'FAILED');

/*
Operational index for investigating terminal failures.
*/

CREATE INDEX idx_outbox_dead
    ON outbox.events (
        created_at,
        event_id
    )
    WHERE status = 'DEAD';

RESET ROLE;