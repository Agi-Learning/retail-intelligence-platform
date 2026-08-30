from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPOSITORY_ROOT / "applications" / "backend"
_SERVICE = _BACKEND / "services" / "identity-service"


def test_identity_service_is_registered() -> None:
    settings = (_BACKEND / "settings.gradle.kts").read_text(encoding="utf-8")

    assert ':services:identity-service' in settings


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
        / "IdentityServiceApplication.java"
    )

    text = application.read_text(encoding="utf-8")

    assert "@SpringBootApplication" in text
    assert "SpringApplication.run" in text
