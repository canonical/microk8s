import os
import stat
from copy import deepcopy
from pathlib import Path
from unittest.mock import mock_open, patch

import jsonschema
import pytest
import yaml

from addons import (
    check_exists,
    check_is_executable,
    get_addons_list,
    validate_addons_file,
    validate_addons_repo,
    validate_yaml_schema,
)
from common.utils import parse_xable_addon_args


ADDONS = [
    ("core", "addon1"),
    ("core", "addon2"),
    ("community", "addon3"),
    ("core", "conflict"),
    ("community", "conflict"),
]


@pytest.mark.parametrize(
    "args, result",
    [
        (["addon1"], [("core", "addon1", [])]),
        (["core/conflict"], [("core", "conflict", [])]),
        (["community/conflict"], [("community", "conflict", [])]),
        (["community/conflict", "--with-arg"], [("community", "conflict", ["--with-arg"])]),
        (["addon1", "--with-arg"], [("core", "addon1", ["--with-arg"])]),
        (
            ["addon1:arg1", "addon2:arg2", "addon3"],
            [
                ("core", "addon1", ["arg1"]),
                ("core", "addon2", ["arg2"]),
                ("community", "addon3", []),
            ],
        ),
        (
            ["addon1:arg1", "addon2:arg2", "community/conflict"],
            [
                ("core", "addon1", ["arg1"]),
                ("core", "addon2", ["arg2"]),
                ("community", "conflict", []),
            ],
        ),
        (
            ["core/addon1:arg1", "addon2:arg2", "community/conflict:arg3"],
            [
                ("core", "addon1", ["arg1"]),
                ("core", "addon2", ["arg2"]),
                ("community", "conflict", ["arg3"]),
            ],
        ),
    ],
)
def test_parse_addons_args(args, result):
    addons = parse_xable_addon_args(args, ADDONS)
    assert addons == result


TEST_ADDON_NAME = "foo"
VALID_ADDONS = {
    "microk8s-addons": {
        "addons": [
            {
                "name": TEST_ADDON_NAME,
                "description": "bar",
                "version": "1.1.1",
                "check_status": "foobar",
                "supported_architectures": ["arm64", "amd64"],
            }
        ]
    }
}
INVALID_ADDONS = deepcopy(VALID_ADDONS)
# Remove one of the required properties of an addon in the addons list
INVALID_ADDONS["microk8s-addons"]["addons"][0].pop("check_status")


def test_validate_yaml_schema():
    validate_yaml_schema(VALID_ADDONS)


def test_validate_yaml_schema_raises_error_if_no_schema_conformant():
    with pytest.raises(jsonschema.ValidationError):
        validate_yaml_schema(INVALID_ADDONS)


def test_validate_addons_file_raises_error_if_not_found():
    with pytest.raises(SystemExit):
        validate_addons_file(Path("/some/path"))


def test_validate_addons_file_raises_error_invalid_yaml():
    with patch("addons.open", mock_open(read_data="unbalanced blackets: ][")):
        with pytest.raises(SystemExit):
            validate_addons_file(Path("/some/path"))


def test_validate_addons_file_raises_error_if_not_schema_conformant():
    with patch("addons.open", mock_open(read_data=yaml.dump(INVALID_ADDONS))):
        with pytest.raises(SystemExit):
            validate_addons_file(Path("/some/path"))


def test_get_addons_list():
    with patch("addons.open", mock_open(read_data=yaml.dump(VALID_ADDONS))):
        assert get_addons_list(Path("/some/path")) == [TEST_ADDON_NAME]


@pytest.fixture(scope="function")
def valid_repo_dir(tmp_path):
    repo_dir = tmp_path / "myrepo"
    repo_dir.mkdir()
    addons_yaml = repo_dir / "addons.yaml"
    addons_yaml.write_text(yaml.dump(VALID_ADDONS))

    addons = repo_dir / "addons"
    addons.mkdir()
    myaddon = addons / TEST_ADDON_NAME
    myaddon.mkdir()

    everyone_can_exec = stat.S_IXGRP | stat.S_IXUSR | stat.S_IEXEC

    enable = myaddon / "enable"
    enable.write_text("echo 1")
    enable.chmod(everyone_can_exec)

    disable = myaddon / "disable"
    disable.write_text("echo 0")
    disable.chmod(everyone_can_exec)

    yield repo_dir


def test_validate_addons_repo(valid_repo_dir):
    validate_addons_repo(valid_repo_dir)


@pytest.fixture(scope="function")
def valid_addon_dir(valid_repo_dir):
    yield valid_repo_dir / "addons" / TEST_ADDON_NAME


@pytest.fixture(scope="function")
def addon_missing_enable(valid_addon_dir):
    enable = valid_addon_dir / "enable"
    os.remove(enable)
    yield valid_addon_dir


def test_check_exists(valid_addon_dir):
    hook = valid_addon_dir / "enable"
    check_exists(hook)


def test_check_exists_raises_error_if_enable_missing(addon_missing_enable):
    hook = addon_missing_enable / "enable"
    with pytest.raises(SystemExit):
        check_exists(hook)


@pytest.fixture(scope="function")
def addon_with_wrong_permission(valid_addon_dir):
    enable = valid_addon_dir / "enable"
    # Change to mode to read-only by the owner
    enable.chmod(stat.S_IREAD)
    yield valid_addon_dir


def test_check_is_executable(valid_addon_dir):
    hook = valid_addon_dir / "enable"
    check_is_executable(hook)


def test_check_is_executable_raises_error_wrong_permissions(addon_with_wrong_permission):
    hook = addon_with_wrong_permission / "enable"
    with pytest.raises(SystemExit):
        check_is_executable(hook)
