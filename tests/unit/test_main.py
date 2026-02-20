"""Unit tests for telos.main — verify commands exist."""

from typer.testing import CliRunner

from telos.main import app

runner = CliRunner()


class TestMainCommands:
    """Verify all expected CLI commands are registered."""

    def test_help_exits_zero(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_list_skills_command_exists(self):
        result = runner.invoke(app, ["list-skills", "--help"])
        assert result.exit_code == 0

    def test_agents_command_exists(self):
        result = runner.invoke(app, ["agents", "--help"])
        assert result.exit_code == 0

    def test_install_command_exists(self):
        result = runner.invoke(app, ["install", "--help"])
        assert result.exit_code == 0

    def test_uninstall_command_exists(self):
        result = runner.invoke(app, ["uninstall", "--help"])
        assert result.exit_code == 0

    def test_init_command_exists(self):
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
