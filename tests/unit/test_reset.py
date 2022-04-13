from click.testing import CliRunner
from reset import reset as command


def test_command_help_arguments():
    runner = CliRunner()
    for help_arg in ("-h", "--help"):
        result = runner.invoke(command, [help_arg])
        assert result.exit_code == 0
        assert "Return the MicroK8s node to the default initial state" in result.output
