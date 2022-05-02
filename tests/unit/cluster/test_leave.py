from click.testing import CliRunner
from leave import leave as command


def test_command_help_arguments():
    runner = CliRunner()
    for help_arg in ("-h", "--help"):
        result = runner.invoke(command, [help_arg])
        assert result.exit_code == 0
        assert "The node will depart from the cluster it is in" in result.output
