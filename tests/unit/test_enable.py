from click.testing import CliRunner
from enable import enable as command
from unittest.mock import patch


def test_command_help_arguments():
    runner = CliRunner()
    for help_arg in ("-h", "--help"):
        result = runner.invoke(command, [help_arg])
        assert result.exit_code == 0
        assert "Enable a MicroK8s addon" in result.output


def test_command_errors_if_no_arguments():
    runner = CliRunner()
    result = runner.invoke(command, [])
    assert result.exit_code != 0
    assert "Error: Missing argument" in result.output


@patch("enable.xable")
def test_command_shows_addon_help_message(xable_mock):
    runner = CliRunner()
    for help_flag in ("-h", "--help"):
        result = runner.invoke(command, ["dns", "--", help_flag])
        assert result.output.startswith("Addon dns does not yet have a help message.")
        xable_mock.assert_not_called()
