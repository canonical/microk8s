from version import get_snap_version, get_snap_revision
import os


def test_get_snap_version():
    os.environ["SNAP_VERSION"] = "v1.21.11"
    assert get_snap_version() == "v1.21.11"


def test_get_snap_revision():
    os.environ["SNAP_REVISION"] = "3086"
    assert get_snap_revision() == "3086"
