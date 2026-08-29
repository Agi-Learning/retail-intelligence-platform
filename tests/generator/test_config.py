from pathlib import Path

import pytest
from pydantic import ValidationError

from retail_intelligence_platform.generator.config import (
    GeneratorSettings,
)


def test_default_settings_are_safe() -> None:
    settings = GeneratorSettings()

    assert settings.host == "127.0.0.1"
    assert settings.port == 5439
    assert settings.database == "retail_platform"
    assert settings.user == "retail_app"
    assert settings.profile == "small"
    assert settings.batch_size == 5_000

    assert "password" not in settings.safe_connection_label
    assert "@" in settings.safe_connection_label


def test_profile_is_normalized() -> None:
    settings = GeneratorSettings(profile=" MEDIUM ")

    assert settings.profile == "medium"


def test_unknown_profile_is_rejected() -> None:
    with pytest.raises(
        ValidationError,
        match="Unknown profile",
    ):
        GeneratorSettings(profile="unknown")


def test_invalid_batch_size_is_rejected() -> None:
    with pytest.raises(ValidationError):
        GeneratorSettings(batch_size=99)


def test_password_is_loaded_from_file(
    tmp_path: Path,
) -> None:
    password_file = tmp_path / "password.txt"
    password_file.write_text(
        "test-only-password\n",
        encoding="utf-8",
    )

    settings = GeneratorSettings(password_file=password_file)

    password = settings.load_password()

    assert password.get_secret_value() == "test-only-password"
    assert "test-only-password" not in str(password)


def test_missing_password_file_is_rejected(
    tmp_path: Path,
) -> None:
    settings = GeneratorSettings(password_file=tmp_path / "missing.txt")

    with pytest.raises(
        FileNotFoundError,
        match="does not exist",
    ):
        settings.load_password()


def test_blank_database_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        GeneratorSettings(database=" ")
