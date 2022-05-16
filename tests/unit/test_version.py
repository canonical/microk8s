from version import get_snap_version
from version import get_snap_revision
from version import get_upstream_versions
from unittest.mock import mock_open, patch
from pathlib import Path
import json
import os


TEST_VERSIONS = {"kube": "v1.21", "cni": "0.0.1"}
TEST_SNAP_PATH = "/home/me/snap/microk8s/current"


def test_get_snap_version():
    os.environ["SNAP_VERSION"] = "v1.21.11"
    assert get_snap_version() == "v1.21.11"


def test_get_snap_revision():
    os.environ["SNAP_REVISION"] = "3086"
    assert get_snap_revision() == "3086"


def test_get_upstream_versions():
    os.environ["SNAP"] = TEST_SNAP_PATH
    open_mock = mock_open(read_data=json.dumps(TEST_VERSIONS))
    with patch("version.open", open_mock):

        assert get_upstream_versions() == TEST_VERSIONS

        expected_path = Path(TEST_SNAP_PATH) / "versions.json"
        open_mock.assert_called_once_with(expected_path, mode="r")
