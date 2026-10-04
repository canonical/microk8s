from click.testing import CliRunner
from disable import disable as command
from unittest.mock import patch


def test_command_help_arguments():
    runner = CliRunner()
    for help_arg in ("-h", "--help"):
        result = runner.invoke(command, [help_arg])
        assert result.exit_code == 0
        assert "Disable one or more MicroK8s addons" in result.output


def test_command_errors_if_no_arguments():
    runner = CliRunner()
    result = runner.invoke(command, [])
    assert result.exit_code != 0
    assert "Error: Missing argument" in result.output


@patch("disable.xable")
def test_command_shows_addon_help_message(xable_mock):
    runner = CliRunner()
    for help_flag in ("-h", "--help"):
        result = runner.invoke(command, ["dns", "--", help_flag])
        assert result.output.startswith("Addon dns does not yet have a help message.")
        xable_mock.assert_not_called()


@patch("disable.wait_for_ready", return_value=False)
@patch("disable.ensure_started")
@patch("disable.exit_if_no_permission")
@patch("disable.is_cluster_locked")
@patch("disable.xable")
def test_command_errors_if_cluster_not_ready(
    xable_mock, is_locked_mock, no_perm_mock, started_mock, wait_mock
):
    runner = CliRunner()
    result = runner.invoke(command, ["dns"])
    assert result.exit_code != 0
    assert "MicroK8s is not ready" in result.output
    xable_mock.assert_not_called()


@patch("disable.wait_for_ready", return_value=True)
@patch("disable.ensure_started")
@patch("disable.exit_if_no_permission")
@patch("disable.is_cluster_locked")
@patch("disable.xable")
def test_command_succeeds_when_cluster_ready(
    xable_mock, is_locked_mock, no_perm_mock, started_mock, wait_mock
):
    runner = CliRunner()
    result = runner.invoke(command, ["dns"])
    assert result.exit_code == 0
    xable_mock.assert_called_once_with("disable", ("dns",))
