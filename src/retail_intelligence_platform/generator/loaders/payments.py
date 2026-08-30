"""Transactional loading for payment records."""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

import psycopg

from retail_intelligence_platform.generator.config import (
    GeneratorSettings,
)
from retail_intelligence_platform.generator.domains.payments import (
    PaymentAttemptRecord,
    PaymentRecord,
    PaymentStatusHistoryRecord,
    generate_payment_attempts,
    generate_payment_status_history,
    generate_payments,
    payment_attempt_count,
)
from retail_intelligence_platform.generator.loaders.catalog import (
    batched,
)
from retail_intelligence_platform.generator.profiles import (
    GenerationProfile,
)


@dataclass(frozen=True, slots=True)
class PaymentLoadResult:
    payments: int
    attempts: int
    status_history: int
    retry_payments: int
    total_paid: Decimal
    total_refunded: Decimal

    @property
    def total_rows(self) -> int:
        return self.payments + self.attempts + self.status_history


def load_payments(
    settings: GeneratorSettings,
    profile: GenerationProfile,
) -> PaymentLoadResult:
    """Load payment records in one transaction."""

    password = settings.load_password()

    with (
        psycopg.connect(
            host=settings.host,
            port=settings.port,
            dbname=settings.database,
            user=settings.user,
            password=password.get_secret_value(),
            connect_timeout=(settings.connect_timeout_seconds),
            application_name="retail-payment-loader",
        ) as connection,
        connection.cursor() as cursor,
    ):
        _load_payments(
            cursor,
            generate_payments(profile),
            settings.batch_size,
        )

        _load_payment_attempts(
            cursor,
            generate_payment_attempts(profile),
            settings.batch_size,
        )

        _load_status_history(
            cursor,
            generate_payment_status_history(profile),
            settings.batch_size,
        )

        result = _read_generated_counts(cursor)

        _validate_loaded_counts(
            result,
            profile,
        )

        connection.commit()

    return result


def _load_payments(
    cursor: psycopg.Cursor,
    records: Iterable[PaymentRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO payment.payments (
            public_id,
            order_id,
            status,
            currency_code,
            requested_amount,
            paid_amount,
            refunded_amount,
            payment_method,
            provider_name,
            provider_payment_reference,
            idempotency_key,
            initiated_at,
            completed_at,
            created_at,
            updated_at
        )
        SELECT
            %(public_id)s,
            orders.order_id,
            %(status)s,
            %(currency_code)s,
            %(requested_amount)s,
            %(paid_amount)s,
            %(refunded_amount)s,
            %(payment_method)s,
            %(provider_name)s,
            %(provider_payment_reference)s,
            %(idempotency_key)s,
            %(initiated_at)s,
            %(completed_at)s,
            %(created_at)s,
            %(updated_at)s
        FROM commerce.orders AS orders
        WHERE orders.public_id =
            %(order_public_id)s
        ON CONFLICT (idempotency_key)
        DO UPDATE SET
            status = EXCLUDED.status,
            paid_amount = EXCLUDED.paid_amount,
            refunded_amount =
                EXCLUDED.refunded_amount,
            payment_method =
                EXCLUDED.payment_method,
            provider_name =
                EXCLUDED.provider_name,
            provider_payment_reference =
                EXCLUDED.provider_payment_reference,
            completed_at = EXCLUDED.completed_at,
            updated_at = EXCLUDED.updated_at,
            version =
                payment.payments.version + 1;
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "public_id": record.public_id,
                    "order_public_id": (record.order_public_id),
                    "status": record.status,
                    "currency_code": (record.currency_code),
                    "requested_amount": (record.requested_amount),
                    "paid_amount": (record.paid_amount),
                    "refunded_amount": (record.refunded_amount),
                    "payment_method": (record.payment_method),
                    "provider_name": (record.provider_name),
                    "provider_payment_reference": (record.provider_payment_reference),
                    "idempotency_key": (record.idempotency_key),
                    "initiated_at": (record.initiated_at),
                    "completed_at": (record.completed_at),
                    "created_at": (record.created_at),
                    "updated_at": (record.updated_at),
                }
                for record in batch
            ],
        )


def _load_payment_attempts(
    cursor: psycopg.Cursor,
    records: Iterable[PaymentAttemptRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO payment.payment_attempts (
            payment_id,
            attempt_number,
            status,
            provider_request_id,
            provider_response_code,
            failure_reason,
            requested_at,
            responded_at
        )
        SELECT
            payments.payment_id,
            %(attempt_number)s,
            %(status)s,
            %(provider_request_id)s,
            %(provider_response_code)s,
            %(failure_reason)s,
            %(requested_at)s,
            %(responded_at)s
        FROM payment.payments AS payments
        WHERE payments.public_id =
            %(payment_public_id)s
        ON CONFLICT (
            payment_id,
            attempt_number
        )
        DO NOTHING;
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "payment_public_id": (record.payment_public_id),
                    "attempt_number": (record.attempt_number),
                    "status": record.status,
                    "provider_request_id": (record.provider_request_id),
                    "provider_response_code": (record.provider_response_code),
                    "failure_reason": (record.failure_reason),
                    "requested_at": (record.requested_at),
                    "responded_at": (record.responded_at),
                }
                for record in batch
            ],
        )


def _load_status_history(
    cursor: psycopg.Cursor,
    records: Iterable[PaymentStatusHistoryRecord],
    batch_size: int,
) -> None:
    statement = """
        INSERT INTO payment.payment_status_history (
            payment_id,
            previous_status,
            new_status,
            reason,
            changed_at
        )
        SELECT
            payments.payment_id,
            %(previous_status)s,
            %(new_status)s,
            %(reason)s,
            %(changed_at)s
        FROM payment.payments AS payments
        WHERE payments.public_id =
                %(payment_public_id)s
          AND NOT EXISTS (
              SELECT 1
              FROM payment.payment_status_history
                  AS existing
              WHERE existing.payment_id =
                      payments.payment_id
                AND existing.previous_status
                    IS NOT DISTINCT FROM
                    %(previous_status)s
                AND existing.new_status =
                    %(new_status)s
                AND existing.changed_at =
                    %(changed_at)s
          );
    """

    for batch in batched(records, batch_size):
        cursor.executemany(
            statement,
            [
                {
                    "payment_public_id": (record.payment_public_id),
                    "previous_status": (record.previous_status),
                    "new_status": (record.new_status),
                    "reason": record.reason,
                    "changed_at": (record.changed_at),
                }
                for record in batch
            ],
        )


def _read_generated_counts(
    cursor: psycopg.Cursor,
) -> PaymentLoadResult:
    cursor.execute(
        """
        SELECT
            count(*),
            COALESCE(sum(paid_amount), 0),
            COALESCE(sum(refunded_amount), 0)
        FROM payment.payments
        WHERE idempotency_key LIKE 'payment-%';
        """
    )

    payment_row = cursor.fetchone()

    if payment_row is None:
        raise RuntimeError("Payment count query returned no result")

    cursor.execute(
        """
        SELECT
            count(*),
            count(*) FILTER (
                WHERE attempt_count > 1
            )
        FROM (
            SELECT
                payments.payment_id,
                count(attempt.payment_attempt_id)
                    AS attempt_count
            FROM payment.payments AS payments
            LEFT JOIN payment.payment_attempts
                AS attempt
              ON attempt.payment_id =
                 payments.payment_id
            WHERE payments.idempotency_key
                LIKE 'payment-%'
            GROUP BY payments.payment_id
        ) AS payment_attempt_counts;
        """
    )

    attempt_summary = cursor.fetchone()

    if attempt_summary is None:
        raise RuntimeError("Payment-attempt query returned no result")

    cursor.execute(
        """
        SELECT count(*)
        FROM payment.payment_attempts AS attempt
        JOIN payment.payments AS payments
          ON payments.payment_id =
             attempt.payment_id
        WHERE payments.idempotency_key
            LIKE 'payment-%';
        """
    )

    attempt_row = cursor.fetchone()

    if attempt_row is None:
        raise RuntimeError("Attempt count query returned no result")

    cursor.execute(
        """
        SELECT count(*)
        FROM payment.payment_status_history
            AS history
        JOIN payment.payments AS payments
          ON payments.payment_id =
             history.payment_id
        WHERE payments.idempotency_key
            LIKE 'payment-%';
        """
    )

    history_row = cursor.fetchone()

    if history_row is None:
        raise RuntimeError("Payment-history query returned no result")

    return PaymentLoadResult(
        payments=payment_row[0],
        attempts=attempt_row[0],
        status_history=history_row[0],
        retry_payments=attempt_summary[1],
        total_paid=payment_row[1],
        total_refunded=payment_row[2],
    )


def _validate_loaded_counts(
    result: PaymentLoadResult,
    profile: GenerationProfile,
) -> None:
    expected_attempts = payment_attempt_count(profile)

    expected_retries = expected_attempts - profile.order_count

    expected = {
        "payments": profile.order_count,
        "attempts": expected_attempts,
        "status_history": (profile.order_count * 2),
        "retry_payments": expected_retries,
    }

    actual = {
        "payments": result.payments,
        "attempts": result.attempts,
        "status_history": result.status_history,
        "retry_payments": result.retry_payments,
    }

    errors = [
        f"{name}: expected {expected[name]}, found {actual[name]}"
        for name in expected
        if actual[name] != expected[name]
    ]

    if result.total_refunded > result.total_paid:
        errors.append("total refunded amount exceeds total paid amount")

    if errors:
        raise RuntimeError("Payment validation failed:\n- " + "\n- ".join(errors))
