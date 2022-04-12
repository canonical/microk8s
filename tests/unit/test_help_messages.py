from click.testing import CliRunner
from enable import enable as enable_command
from disable import disable as disable_command
from dashboard_proxy import dashboard_proxy as dashboard_proxy_command
from reset import reset as reset_command
from refresh_certs import refresh_certs as refresh_certs_command
import pytest


@pytest.mark.parametrize(
    "command,no_args_should_error,help_string",
    [
        (enable_command, True, "Enables a MicroK8s addon"),
        (disable_command, True, "Disables one or more MicroK8s addons."),
        (
            dashboard_proxy_command,
            False,
            "Enables the dashboard add-on and configures port-forwarding",
        ),
        (reset_command, False, "Returns the MicroK8s node to the default initial state"),
        (refresh_certs_command, False, "Replace the CA certificates with the ca.crt and ca.key"),
    ],
)
def test_help_arguments_are_consistent_across_commands(command, no_args_should_error, help_string):
    runner = CliRunner()
    for help_arg in ("-h", "--help"):
        result = runner.invoke(command, [help_arg])
        assert help_string in result.output

    if no_args_should_error:
        result = runner.invoke(command, [])
        assert result.exit_code != 0
