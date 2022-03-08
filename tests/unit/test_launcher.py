import os
from unittest.mock import patch
from click.testing import CliRunner
from launcher import launcher as command


class TestLauncher(object):
    def setup_class(self):
        dirname, filename = os.path.split(os.path.abspath(__file__))
        self._invalid_yaml = os.path.join(dirname, "yamls/invalid-launcher.yaml")
        self._valid_yaml = os.path.join(dirname, "yamls/valid-launcher.yaml")

    def test_launcher(self):
        """
        Test that we can handle a valid configuration file
        """
        runner = CliRunner()
        result = runner.invoke(command, [self._valid_yaml, "--dry"])
        assert result.exit_code == 0
        assert "enable dns" in result.output
        assert "disable ingress" in result.output
        assert "enable foo --arg-a=A --arg-b=B" in result.output

    def test_launcher_invalid(self):
        """
        Test that we fail on an invalid configuration file
        """
        runner = CliRunner()
        result = runner.invoke(command, [self._invalid_yaml, "--dry"])
        assert result.exit_code == 1

    @patch("launcher.check_output")
    def test_cli_launcher(self, mock_check_output):
        """
        Test that we really call subprocess check_output
        """
        runner = CliRunner()
        runner.invoke(command, [self._valid_yaml])
        assert mock_check_output.call_count == 3
