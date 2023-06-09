import os
import pytest
from unittest.mock import patch, call, Mock
from click.testing import CliRunner

from refresh_certs import (
    refresh_certs,
    restart,
    reproduce_all_root_ca_certs,
    reproduce_front_proxy_client_cert,
    reproduce_server_cert,
)


class TestRefreshCerts(object):
    @patch("subprocess.check_call")
    def test_restart(self, mock_check_call):
        restart()
        # We stop and start microk8s
        assert mock_check_call.call_count == 2

    @patch("common.cluster.utils.get_arg")
    @patch("subprocess.Popen")
    @patch("subprocess.check_call")
    def test_reproduce_all_root_ca_certs(self, mock_check_call, mock_subproc_popen, mock_get_arg):
        process_mock = Mock()
        mock_subproc_popen.return_value = process_mock
        mock_get_arg.return_value = "known_tokens.csv"

        reproduce_all_root_ca_certs()

        """
        Make sure we:
        1. remove the ca.crt
        2. call produce_certs
        3. call update_configs that also restarts microk8s
        """
        snapdata_path = os.environ.get("SNAP_DATA")
        assert (
            call("rm -rf {}/certs/ca.crt".format(snapdata_path).split())
            in mock_check_call.call_args_list
        )
        assert mock_check_call.called
        assert mock_subproc_popen.called
        assert self.is_argument_in_call(mock_subproc_popen, "produce_certs")
        assert self.is_argument_in_call(mock_subproc_popen, "update_configs")

    @patch("refresh_certs.restart")
    @patch("subprocess.check_call")
    def test_reproduce_front_proxy_client_cert(self, mock_check_call, mock_restart):
        """
        Make sure we:
        1. remove the front-proxy-client.crt
        2. call gen_proxy_client_cert
        3. restart microk8s
        """
        reproduce_front_proxy_client_cert()

        snapdata_path = os.environ.get("SNAP_DATA")
        cmd = "rm -rf {}/certs/front-proxy-client.crt".format(snapdata_path).split()
        assert call(cmd) in mock_check_call.call_args_list
        assert mock_check_call.called
        assert mock_restart.called
        assert self.is_argument_in_call(mock_check_call, "gen_proxy_client_cert")

    @patch("refresh_certs.restart")
    @patch("subprocess.check_call")
    def test_reproduce_server_cert(self, mock_check_call, mock_restart):
        """
        Make sure we:
        1. remove the server.crt
        2. call gen_server_cert
        3. restart microk8s
        """
        reproduce_server_cert()

        snapdata_path = os.environ.get("SNAP_DATA")
        assert (
            call("rm -rf {}/certs/server.crt".format(snapdata_path).split())
            in mock_check_call.call_args_list
        )
        assert mock_check_call.called
        assert mock_restart.called
        assert self.is_argument_in_call(mock_check_call, "gen_server_cert")

    def is_argument_in_call(self, mock_function, argument_substring):
        """Search for a substring in the list of arguments in all calls of a mocked function"""
        for calls in mock_function.call_args_list:
            # calls is the list of calls
            for arglist in calls.args:
                # list of arguments in call
                for arg in arglist:
                    if argument_substring in arg:
                        return True
        return False

    @pytest.mark.parametrize(
        "ca_dir,undo,check,cert,help,expected_output,expected_err_code",
        [
            (None, None, True, "ca.crt", None, "Please select only one of the options", 2),
            (None, True, True, None, None, "Please select only one of the options", 2),
            (None, True, None, "ca.crt", None, "Please select only one of the options", 2),
            (None, True, None, "ca.crt", True, "Usage:", 0),
            ("/some/path", True, None, None, None, "does not exist", 2),
            ("/", True, None, None, None, "options in combination", 1),
            (None, True, None, "wrong_file", None, "Invalid value", 2),
        ],
    )
    def test_refresh_cert_errors(
        self, ca_dir, undo, check, cert, help, expected_output, expected_err_code
    ):
        """
        Test conditions under which the upgrade should not continue
        """
        runner = CliRunner()
        args = []
        if ca_dir:
            args.append(ca_dir)
        if undo:
            args.append("-u")
        if check:
            args.append("-c")
        if cert:
            args.append("-e")
            args.append(cert)
        if help:
            args.append("-h")
        result = runner.invoke(refresh_certs, args)
        assert expected_output in result.output
        assert result.exit_code == expected_err_code


def test_command_help_arguments():
    runner = CliRunner()
    for help_arg in ("-h", "--help"):
        result = runner.invoke(refresh_certs, [help_arg])
        assert result.exit_code == 0
        assert "Replace the CA certificates with the ca.crt and ca.key" in result.output
