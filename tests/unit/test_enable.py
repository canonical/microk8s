from click.testing import CliRunner
from enable import enable as enable_command
from unittest.mock import patch


@patch("enable.xable")
def test_enable_command_shows_addon_help_message(xable_mock):
    runner = CliRunner()
    for help_flag in ("-h", "--help"):
        result = runner.invoke(enable_command, ["dns", "--", help_flag])
        assert result.output.startswith("Addon dns does not yet have a help message.")
        xable_mock.assert_not_called()
