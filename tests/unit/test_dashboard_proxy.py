from click.testing import CliRunner
from dashboard_proxy import dashboard_proxy as command


def test_command_help_arguments():
    runner = CliRunner()
    for help_arg in ("-h", "--help"):
        result = runner.invoke(command, [help_arg])
        assert result.exit_code == 0
        assert "Enable the dashboard add-on and configures port-forwarding" in result.output
