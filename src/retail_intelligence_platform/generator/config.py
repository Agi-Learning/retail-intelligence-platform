"""Validated configuration for source-data generation."""

from pathlib import Path
from typing import Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from retail_intelligence_platform.generator.profiles import get_profile


class GeneratorSettings(BaseSettings):
    """Environment-backed generator configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RETAIL_GENERATOR_",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    host: str = "127.0.0.1"
    port: int = Field(default=5439, ge=1, le=65_535)
    database: str = "retail_platform"
    user: str = "retail_app"

    password_file: Path = Path("secrets/postgres/app_password.txt")

    seed: int = 20_260_829

    batch_size: int = Field(
        default=5_000,
        ge=100,
        le=100_000,
    )

    profile: str = "small"

    connect_timeout_seconds: int = Field(
        default=10,
        ge=1,
        le=60,
    )

    @field_validator(
        "host",
        "database",
        "user",
        mode="before",
    )
    @classmethod
    def validate_nonblank_text(cls, value: object) -> object:
        """Reject empty connection identifiers."""

        if isinstance(value, str) and not value.strip():
            raise ValueError("value must not be blank")

        return value

    @field_validator("profile", mode="before")
    @classmethod
    def normalize_profile(cls, value: object) -> str:
        """Normalize and validate the configured profile."""

        if not isinstance(value, str):
            raise TypeError("profile must be a string")

        normalized = value.strip().lower()
        get_profile(normalized)

        return normalized

    @model_validator(mode="after")
    def validate_password_path(self) -> Self:
        """Reject directory paths before connection time."""

        if self.password_file.exists() and not self.password_file.is_file():
            raise ValueError("password_file must point to a regular file")

        return self

    def load_password(self) -> SecretStr:
        """Read the database password without logging it."""

        try:
            password = self.password_file.read_text(encoding="utf-8").strip()
        except FileNotFoundError as error:
            raise FileNotFoundError(
                f"Generator password file does not exist: {self.password_file}"
            ) from error

        if not password:
            raise ValueError(f"Generator password file is empty: {self.password_file}")

        return SecretStr(password)

    @property
    def safe_connection_label(self) -> str:
        """Return connection metadata containing no password."""

        return f"postgresql://{self.user}@{self.host}:{self.port}/{self.database}"
