from typer.testing import CliRunner

import retail_intelligence_platform.generator.cli as cli_module
from retail_intelligence_platform.generator.cli import app
from retail_intelligence_platform.generator.loaders.catalog import (
    CatalogLoadResult,
)

runner = CliRunner()


def test_cli_displays_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Generate deterministic retail" in result.stdout
    assert "validate" in result.stdout
    assert "plan" in result.stdout
    assert "profiles" in result.stdout


def test_profiles_command_lists_profiles() -> None:
    result = runner.invoke(app, ["profiles"])

    assert result.exit_code == 0
    assert "smoke" in result.stdout
    assert "small" in result.stdout
    assert "medium" in result.stdout
    assert "large" in result.stdout
    assert "stress" in result.stdout


def test_smoke_plan_displays_total() -> None:
    result = runner.invoke(
        app,
        ["plan", "--profile", "smoke"],
    )

    assert result.exit_code == 0
    assert "Profile: smoke" in result.stdout
    assert "identity.customers" in result.stdout
    assert "commerce.orders" in result.stdout
    assert "3,046" in result.stdout


def test_unknown_profile_fails_safely() -> None:
    result = runner.invoke(
        app,
        ["plan", "--profile", "unknown"],
    )

    assert result.exit_code != 0
    assert "Unknown profile" in result.output


def test_large_catalogue_load_requires_yes() -> None:
    result = runner.invoke(
        app,
        [
            "load-catalog",
            "--profile",
            "large",
        ],
    )

    assert result.exit_code == 2
    assert "Execution blocked" in result.stdout
    assert "rerun with --yes" in result.stdout


def test_large_catalogue_load_with_yes_executes(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        cli_module,
        "check_database",
        lambda settings: None,
    )

    monkeypatch.setattr(
        cli_module,
        "load_catalog_records",
        lambda settings, profile: CatalogLoadResult(
            brands=1_000,
            categories=2_500,
            products=200_000,
            product_prices=400_000,
        ),
    )

    result = runner.invoke(
        app,
        [
            "load-catalog",
            "--profile",
            "large",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    assert "Catalogue load completed" in result.stdout
    assert "Products: 200,000" in result.stdout


def test_smoke_catalogue_load_does_not_require_yes(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        cli_module,
        "check_database",
        lambda settings: None,
    )

    monkeypatch.setattr(
        cli_module,
        "load_catalog_records",
        lambda settings, profile: CatalogLoadResult(
            brands=5,
            categories=10,
            products=50,
            product_prices=100,
        ),
    )

    result = runner.invoke(
        app,
        [
            "load-catalog",
            "--profile",
            "smoke",
        ],
    )

    assert result.exit_code == 0
    assert "Catalogue load completed" in result.stdout
    assert "Total catalogue rows: 165" in result.stdout


def test_catalogue_loader_failure_is_safe(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        cli_module,
        "check_database",
        lambda settings: None,
    )

    def fail_loader(settings, profile):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(
        cli_module,
        "load_catalog_records",
        fail_loader,
    )

    result = runner.invoke(
        app,
        [
            "load-catalog",
            "--profile",
            "smoke",
        ],
    )

    assert result.exit_code == 1
    assert "Catalogue load failed" in result.stdout
    assert "simulated failure" in result.stdout
