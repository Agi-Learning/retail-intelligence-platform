"""Tests for the shared backend build platform."""

from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPOSITORY_ROOT / "applications" / "backend"


def test_gradle_wrapper_is_pinned() -> None:
    properties = (
        _BACKEND / "gradle" / "wrapper" / "gradle-wrapper.properties"
    ).read_text(encoding="utf-8")

    assert "gradle-9.7.1-bin.zip" in properties
    assert "distributionSha256Sum=" in properties


def test_build_logic_convention_plugin_exists() -> None:
    plugin = (
        _BACKEND
        / "build-logic"
        / "src"
        / "main"
        / "kotlin"
        / "retail.java-service-conventions.gradle.kts"
    )

    contents = plugin.read_text(encoding="utf-8")

    assert "JavaLanguageVersion.of(25)" in contents
    assert "jacoco" in contents
    assert "useJUnitPlatform()" in contents


def test_platform_modules_are_registered() -> None:
    settings = (_BACKEND / "settings.gradle.kts").read_text(encoding="utf-8")

    for module in (
        ":platform:dependency-bom",
        ":platform:service-starter",
        ":platform:security-starter",
        ":platform:kafka-starter",
        ":platform:observability-starter",
        ":platform:testing-starter",
    ):
        assert module in settings


def test_all_platform_build_files_exist() -> None:
    modules = (
        "dependency-bom",
        "service-starter",
        "security-starter",
        "kafka-starter",
        "observability-starter",
        "testing-starter",
    )

    for module in modules:
        path = _BACKEND / "platform" / module / "build.gradle.kts"

        assert path.is_file()


def test_service_starter_contains_common_capabilities() -> None:
    build_file = (
        _BACKEND / "platform" / "service-starter" / "build.gradle.kts"
    ).read_text(encoding="utf-8")

    for dependency in (
        "spring-boot-starter-web",
        "spring-boot-starter-validation",
        "spring-boot-starter-data-jdbc",
        "spring-boot-starter-actuator",
        "flyway-core",
    ):
        assert dependency in build_file
