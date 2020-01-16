import os
import subprocess
import unittest

from click.testing import CliRunner

from cli.microk8s import install


class TestCli(unittest.TestCase):

    def test_install(self):
        self._uninstall_multipass()
        runner = CliRunner()
        result = runner.invoke(install)
        assert result.exit_code == 0
        assert result.output == 'Hello Amy!\n'

    def _uninstall_multipass(self):
        # This is for linux for now
        if os.path.isfile('/snap/bin/multipass') and os.geteuid() == 0:
            print("Removing installed multipass")
            subprocess.check_call("sudo snap remove multipass".split())
            return True
        else:
            return False
