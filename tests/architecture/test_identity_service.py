import csv
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPOSITORY_ROOT / "applications" / "backend"
_SERVICE = _BACKEND / "services" / "identity" / "identity-01"
_MANIFEST = (
    _REPOSITORY_ROOT
    / "docs"
    / "architecture"
    / "generated"
    / "backend_service_contract_manifest.csv"
)


def test_identity_service_is_registered() -> None:
    settings = (_BACKEND / "settings.gradle.kts").read_text(encoding="utf-8")

    assert ":services:identity:identity-01" in settings


def test_identity_service_uses_shared_platform() -> None:
    build = (_SERVICE / "build.gradle.kts").read_text(encoding="utf-8")

    for module in (
        "service-starter",
        "security-starter",
        "kafka-starter",
        "observability-starter",
        "testing-starter",
    ):
        assert f'project(":platform:{module}")' in build


def test_identity_service_has_boot_entrypoint() -> None:
    application = (
        _SERVICE
        / "src"
        / "main"
        / "java"
        / "com"
        / "agilearning"
        / "retail"
        / "identity"
        / "service0001"
        / "Identity01Application.java"
    )

    text = application.read_text(encoding="utf-8")

    assert "package com.agilearning.retail.identity.service0001;" in text
    assert "class Identity01Application" in text
    assert "@SpringBootApplication" in text
    assert "SpringApplication.run" in text


def test_identity_service_matches_manifest_contract() -> None:
    with _MANIFEST.open(newline="", encoding="utf-8") as stream:
        row = next(
            row
            for row in csv.DictReader(stream)
            if row["microservice_name"] == "identity-01"
        )

    assert row["microservice_id"] == "svc-0001"
    assert row["backend_module_path"] == (
        "applications/backend/services/identity/identity-01"
    )
    assert row["java_package"] == (
        "com.agilearning.retail.identity.service0001"
    )
    assert row["application_class"] == "Identity01Application"
    assert row["api_base_path"] == "/api/v1/identity/01"
