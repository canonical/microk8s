import os
import subprocess
import platform
from unittest import mock

import pytest
from click.testing import CliRunner

from cli.microk8s import cli


class TestClass:
    @pytest.mark.skipif(
        platform.system() != "Linux", reason="Add/remove multipass is available on Linux"
    )
    @pytest.mark.skipif(os.getuid() != 0, reason="Add/remove multipass is possible to root")
    @mock.patch("sys.stdin.isatty", return_value=True)
    def test_install_remove_multipass(self, tty_mock):
        """
        We are root on a Linux box.
        Test the install and remove of multipass
        """
        runner = CliRunner()
        # making sure we start on a clean machine with multipass
        result = runner.invoke(cli, "uninstall")
        subprocess.check_call("sudo snap install multipass --classic".split())
        assert os.path.isfile("/snap/bin/multipass")
        assert result.exit_code == 0

        # making sure we start on a clean machine
        result = runner.invoke(cli, "install")
        assert result.exit_code == 0
        assert os.path.isfile("/snap/bin/multipass")

        result = runner.invoke(cli, "status --wait-ready --timeout=60")
        assert result.exit_code == 0

        result = runner.invoke(cli, "install")
        assert os.path.isfile("/snap/bin/multipass")
        assert result.exit_code == 0

    def test_all_cli(self):
        runner = CliRunner()

        # Test no args. We should get an error.
        result = runner.invoke(cli)
        assert result.exit_code == 1

        # Test no args. We should get an error.
        result = runner.invoke(cli, "--help")
        assert result.exit_code == 0

    def test_install_argument_are_validated(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["install", "--mem", "1"])
        assert result.exit_code == 2
        assert "invalid memory value" in result.output

        result = runner.invoke(cli, ["install", "--cpu", "1"])
        assert result.exit_code == 2
        assert "invalid cpu value" in result.output

        result = runner.invoke(cli, ["install", "--disk", "1"])
        assert result.exit_code == 2
        assert "invalid disk value" in result.output
