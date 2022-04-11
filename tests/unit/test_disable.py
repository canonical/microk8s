from click.testing import CliRunner
from disable import disable as disable_command
from unittest.mock import patch


@patch("disable.xable")
def test_disable_command_shows_addon_help_message(xable_mock):
    runner = CliRunner()
    for help_flag in ("-h", "--help"):
        result = runner.invoke(disable_command, ["dns", "--", help_flag])
        assert result.output.startswith("Addon dns does not yet have a help message.")
        xable_mock.assert_not_called()
