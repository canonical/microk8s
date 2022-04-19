from click.testing import CliRunner
from version import version_command as command
from version import get_snap_version
from version import get_snap_revision
from version import get_upstream_versions
from unittest.mock import mock_open, patch
from pathlib import Path
import json


TEST_VERSIONS = {"kube": "v1.21", "cni": "0.0.1"}


def test_command_help_arguments():
    runner = CliRunner()
    for help_arg in ("-h", "--help"):
        result = runner.invoke(command, [help_arg])
        assert result.exit_code == 0
        assert "Show version information of MicroK8s and" in result.output


@patch("version.environ", {"SNAP_VERSION": "v1.21.11"})
def test_get_snap_version():
    assert get_snap_version() == "v1.21.11"


@patch("version.environ", {"SNAP_REVISION": "3086"})
def test_get_snap_revision():
    assert get_snap_revision() == "3086"


@patch("version.environ", {"SNAP": "/home/me/snap/microk8s/current"})
def test_get_upstream_versions():

    open_mock = mock_open(read_data=json.dumps(TEST_VERSIONS))
    with patch("version.open", open_mock):

        assert get_upstream_versions() == TEST_VERSIONS

        expected_path = Path("/home/me/snap/microk8s/current") / "versions.json"
        open_mock.assert_called_once_with(expected_path, mode="r")
