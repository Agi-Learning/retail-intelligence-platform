from typer.testing import CliRunner

from retail_intelligence_platform.generator.cli import app

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
