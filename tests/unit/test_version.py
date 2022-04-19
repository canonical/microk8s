from click.testing import CliRunner
from version import version_command as command
from version import get_upstream_version
from version import get_snap_version_data
from version import _read_versions_file
from version import VERSIONS_FILE
from unittest.mock import mock_open, patch
import pytest
import json


TEST_VERSIONS = {"kube": "v1.21", "cni": "0.0.1"}

TEST_SNAP_LIST_OUTPUT = """Name      Version   Rev   Tracking     Publisher   Notes
microk8s  v1.21.11  3058  1.21/stable  canonical✓  classic
"""


def test_command_help_arguments():
    runner = CliRunner()
    for help_arg in ("-h", "--help"):
        result = runner.invoke(command, [help_arg])
        assert result.exit_code == 0
        assert "Show version information of MicroK8s and" in result.output


@patch("version._read_versions_file", return_value=TEST_VERSIONS)
def test_get_upstream_version(_read_versions_file_mock):
    assert get_upstream_version("kube") == TEST_VERSIONS["kube"]
    assert get_upstream_version("cni") == TEST_VERSIONS["cni"]

    # Check that versions file contents gets cached
    _read_versions_file_mock.assert_called_once()

    with pytest.raises(KeyError):
        get_upstream_version("foobar")


@patch("version.run", return_value=TEST_SNAP_LIST_OUTPUT)
def test_get_snap_version_data(run_mock):
    assert get_snap_version_data() == ("v1.21.11", "3058")
    run_mock.assert_called_once_with("snap", "list", "microk8s")


def test_read_versions_data():
    open_mock = mock_open(read_data=json.dumps(TEST_VERSIONS))
    with patch("version.open", open_mock):

        assert _read_versions_file() == TEST_VERSIONS
        open_mock.assert_called_once_with(VERSIONS_FILE, mode="r")
