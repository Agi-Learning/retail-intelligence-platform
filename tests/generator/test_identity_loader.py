import pytest

from retail_intelligence_platform.generator.loaders.identity import (
    IdentityLoadResult,
    _validate_loaded_counts,
)
from retail_intelligence_platform.generator.profiles import (
    get_profile,
)


def test_identity_result_total() -> None:
    result = IdentityLoadResult(
        customers=20,
        credentials=20,
        addresses=40,
        default_addresses=20,
    )

    assert result.total_rows == 80


def test_smoke_identity_counts_are_valid() -> None:
    _validate_loaded_counts(
        IdentityLoadResult(
            customers=20,
            credentials=20,
            addresses=40,
            default_addresses=20,
        ),
        get_profile("smoke"),
    )


def test_missing_credentials_are_rejected() -> None:
    with pytest.raises(
        RuntimeError,
        match="credentials: expected 20",
    ):
        _validate_loaded_counts(
            IdentityLoadResult(
                customers=20,
                credentials=19,
                addresses=40,
                default_addresses=20,
            ),
            get_profile("smoke"),
        )


def test_duplicate_defaults_are_rejected() -> None:
    with pytest.raises(
        RuntimeError,
        match="default_addresses",
    ):
        _validate_loaded_counts(
            IdentityLoadResult(
                customers=20,
                credentials=20,
                addresses=40,
                default_addresses=21,
            ),
            get_profile("smoke"),
        )
