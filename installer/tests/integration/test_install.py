import os
import subprocess
import unittest

from click.testing import CliRunner

from cli.microk8s import cli


class TestCli(unittest.TestCase):

    def test_install(self):
        self._uninstall_multipass()
        runner = CliRunner()

        # Calling cli without arguments
        result = runner.invoke(cli)
        assert result.exit_code == 1
        assert '--help' in result.output

        # Calling cli without having the VM installed
        result = runner.invoke(cli, "status")
        assert result.exit_code == 1
        assert 'not running' in result.output

    def _uninstall_multipass(self):
        # This is for linux for now
        if os.path.isfile('/snap/bin/multipass') and os.geteuid() == 0:
            print("Removing installed multipass")
            subprocess.check_call("sudo snap remove multipass".split())
            return True
        else:
            return False
