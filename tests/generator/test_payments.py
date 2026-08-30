from collections import Counter, defaultdict

from retail_intelligence_platform.generator.domains.orders import (
    generate_orders,
)
from retail_intelligence_platform.generator.domains.payments import (
    generate_payment_attempts,
    generate_payment_status_history,
    generate_payments,
    payment_attempt_count,
)
from retail_intelligence_platform.generator.profiles import (
    get_profile,
)


def test_smoke_payment_counts() -> None:
    profile = get_profile("smoke")

    assert len(list(generate_payments(profile))) == 100
    assert payment_attempt_count(profile) == 120

    assert len(list(generate_payment_attempts(profile))) == 120

    assert len(list(generate_payment_status_history(profile))) == 200


def test_payment_generation_is_deterministic() -> None:
    profile = get_profile("smoke")

    assert list(generate_payments(profile)) == list(generate_payments(profile))

    assert list(generate_payment_attempts(profile)) == list(
        generate_payment_attempts(profile)
    )


def test_payments_reference_orders() -> None:
    profile = get_profile("smoke")

    order_ids = {order.public_id for order in generate_orders(profile)}

    for payment in generate_payments(profile):
        assert payment.order_public_id in order_ids


def test_payment_amount_constraints() -> None:
    profile = get_profile("small")

    for payment in generate_payments(profile):
        assert payment.requested_amount > 0
        assert payment.paid_amount >= 0
        assert payment.paid_amount <= payment.requested_amount
        assert payment.refunded_amount >= 0
        assert payment.refunded_amount <= payment.paid_amount

        if payment.completed_at is not None:
            assert payment.completed_at >= payment.initiated_at


def test_provider_identifiers_are_unique() -> None:
    profile = get_profile("small")
    payments = list(generate_payments(profile))
    attempts = list(generate_payment_attempts(profile))

    provider_references = [
        payment.provider_payment_reference
        for payment in payments
        if payment.provider_payment_reference is not None
    ]

    request_ids = [attempt.provider_request_id for attempt in attempts]

    assert len(provider_references) == len(set(provider_references))

    assert len(request_ids) == len(set(request_ids))


def test_twenty_smoke_payments_have_retries() -> None:
    profile = get_profile("smoke")

    attempts_by_payment = Counter(
        attempt.payment_public_id for attempt in generate_payment_attempts(profile)
    )

    assert Counter(attempts_by_payment.values()) == {
        1: 80,
        2: 20,
    }


def test_payment_history_matches_final_state() -> None:
    profile = get_profile("smoke")
    histories = defaultdict(list)

    for history in generate_payment_status_history(profile):
        histories[history.payment_public_id].append(history)

    for payment in generate_payments(profile):
        payment_history = histories[payment.public_id]

        assert len(payment_history) == 2
        assert payment_history[0].new_status == "INITIATED"
        assert payment_history[-1].new_status == payment.status
