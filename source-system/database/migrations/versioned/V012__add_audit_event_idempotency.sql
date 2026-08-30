/*
=========================================================
Retail Intelligence Platform
Migration: V012
Purpose:
  - Add a deterministic idempotency key to audit events
  - Preserve append-only runtime permissions
=========================================================
*/

SET ROLE retail_owner;

/*
Existing audit rows may remain NULL.

Generated and externally replayable audit events should supply
a stable UUID so retries can use INSERT ... ON CONFLICT DO NOTHING
without requiring SELECT access to the audit table.
*/

ALTER TABLE audit.audit_events
    ADD COLUMN event_key UUID;

COMMENT ON COLUMN audit.audit_events.event_key IS
    'Optional deterministic key used to suppress duplicate audit-event delivery.';

/*
NULL values remain permitted for audit entries that do not have
an external idempotency key. Non-NULL keys must be globally unique.
*/

CREATE UNIQUE INDEX uq_audit_events_event_key
    ON audit.audit_events (event_key)
    WHERE event_key IS NOT NULL;

RESET ROLE;