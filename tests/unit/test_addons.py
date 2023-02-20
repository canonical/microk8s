import os
import stat
import shutil
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from unittest.mock import mock_open, patch, Mock

import pytest
import yaml

from addons import (
    AddonsYamlFormatError,
    AddonsYamlNotFoundError,
    MissingHookError,
    WrongHookPermissionsError,
    add,
    get_addons_list,
    load_addons_yaml,
    update,
    validate_addons_file,
    validate_addons_repo,
)
from common.utils import parse_xable_addon_args, get_available_addons


ADDONS = [
    ("core", "addon1"),
    ("core", "addon2"),
    ("community", "addon3"),
    ("core", "conflict"),
    ("community", "conflict"),
]


REPO_YAML = """
microk8s-addons:
  description: "List of all addons included in Microk8s."
  addons:
    - name: "dns"
      description: "CoreDNS"
      version: "1.9.0"
      check_status: "pod/coredns"
      supported_architectures:
        - amd64
        - arm64
        - s390x

    - name: "rbac"
      description: "Role-Based Access Control for authorisation"
      version: ""
      check_status: "clusterrole.rbac.authorization.k8s.io/cluster-admin"
      confinement: "strict"
      supported_architectures:
        - arm64
        - amd64
        - s390x

    - name: "dashboard"
      description: "The Kubernetes dashboard"
      version: "2.3.0"
      check_status: "pod/kubernetes-dashboard"
      confinement: "classic"
      supported_architectures:
        - arm64
        - amd64
        - s390x
"""


@pytest.mark.parametrize(
    "confinement, result", [(True, ["dns", "rbac"]), (False, ["dns", "dashboard"])]
)
@patch("common.utils.is_strict")
@patch("os.listdir")
@patch("common.utils.snap_common")
def test_get_available_addons(snap_common_mock, listdir_mock, strict_mock, confinement, result):
    strict_mock.return_value = confinement
    listdir_mock.return_value = ["/a/path/"]
    snap_common_mock.return_value = Path("/common_dir")

    with patch("common.utils.open", mock_open(read_data=REPO_YAML)):
        addons = get_available_addons("amd64")
        assert len(addons) == len(result)
        for addon in addons:
            assert addon["name"] in result


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


@patch("addons.load_addons_yaml", return_value=VALID_ADDONS)
def test_validate_addons_file(load_addons_mock):
    validate_addons_file(Mock())


@patch("addons.load_addons_yaml", return_value=INVALID_ADDONS)
def test_validate_addons_file_raises_if_invalid_format(load_addons_mock):
    with pytest.raises(AddonsYamlFormatError) as err:
        validate_addons_file(Mock())
    assert "Invalid addons.yaml file" in err.value.message


def test_load_addons_raises_on_file_not_found():
    # When addons.yaml file is not found
    with pytest.raises(AddonsYamlNotFoundError) as exc:
        load_addons_yaml(Path("/some/repo"))
    assert exc.value.message == "Error: repository repo does not contain an addons.yaml file"


def test_load_addons_raises_on_invalid_yaml_contents(repo_dir):
    with patch("addons.open", mock_open(read_data="unbalanced blackets: ][")):
        with pytest.raises(AddonsYamlFormatError) as exc:
            load_addons_yaml(repo_dir)
        assert (
            exc.value.message
            == "Yaml format error in addons.yaml file: while parsing a block node expected the node content, but found ']'"  # noqa
        )


def test_get_addons_list():
    with patch("addons.open", mock_open(read_data=yaml.dump(VALID_ADDONS))):
        assert get_addons_list(Path("/some/path")) == [TEST_ADDON_NAME]


def test_validate_addons_repo(repo_dir):
    validate_addons_repo(repo_dir)


def test_validate_addons_repo_raises_on_missing_enable_hook(addon_missing_enable_hook):
    with pytest.raises(MissingHookError) as err:
        validate_addons_repo(addon_missing_enable_hook)
    assert err.value.message == "Missing enable hook for foo addon"


def test_validate_addons_repo_raises_on_missing_disable_hook(addon_missing_disable_hook):
    with pytest.raises(MissingHookError) as err:
        validate_addons_repo(addon_missing_disable_hook)
    assert err.value.message == "Missing disable hook for foo addon"


def test_validate_addons_repo_raises_on_enable_not_executable(enable_not_executable):
    with pytest.raises(WrongHookPermissionsError) as err:
        validate_addons_repo(enable_not_executable)
    assert err.value.message == "enable hook for foo addon needs execute permissions"


def test_validate_addons_repo_raises_on_disable_not_executable(disable_not_executable):
    with pytest.raises(WrongHookPermissionsError) as err:
        validate_addons_repo(disable_not_executable)
    assert err.value.message == "disable hook for foo addon needs execute permissions"


@patch("addons.subprocess")
@patch("addons.snap_common", return_value=Path("/tmp/"))
@patch("addons.get_group", return_value="microk8s")
@patch("addons.validate_addons_repo", side_effect=AddonsYamlFormatError("foo"))
@patch("addons.shutil.rmtree")
def test_add_removes_repo_on_validation_error(
    rm_mock,
    validate_addons_repo_mock,
    get_group_mock,
    snap_common_mock,
    subprocess_mock,
):
    with pytest.raises(SystemExit):
        add.callback("myrepo", "http://github.com/me/myrepo", None, False)

    repo_dir = Path("/tmp/addons/myrepo")
    validate_addons_repo_mock.assert_called_once_with(repo_dir)
    rm_mock.assert_called_once_with(repo_dir)


@pytest.fixture(scope="function")
def repo_dir(tmp_path):
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


@pytest.fixture(scope="function")
def invalid_addons_yaml(tmp_path):
    repo_dir = tmp_path / "invalid_repo"
    repo_dir.mkdir()
    addons_yaml = repo_dir / "addons.yaml"
    addons_yaml.write_text(yaml.dump(INVALID_ADDONS))
    yield repo_dir


@pytest.fixture(scope="function")
def missing_addons_yaml(tmp_path):
    repo_dir = tmp_path / "invalid_repo"
    repo_dir.mkdir()
    yield repo_dir


@pytest.fixture(scope="function")
def addon_missing_enable_hook(repo_dir):
    addon_dir = repo_dir / "addons" / TEST_ADDON_NAME
    os.remove(addon_dir / "enable")
    yield repo_dir


@pytest.fixture(scope="function")
def addon_missing_disable_hook(repo_dir):
    addon_dir = repo_dir / "addons" / TEST_ADDON_NAME
    os.remove(addon_dir / "disable")
    yield repo_dir


@pytest.fixture(scope="function")
def enable_not_executable(repo_dir):
    addon_dir = repo_dir / "addons" / TEST_ADDON_NAME
    (addon_dir / "enable").chmod(stat.S_IREAD)
    yield repo_dir


@pytest.fixture(scope="function")
def disable_not_executable(repo_dir):
    addon_dir = repo_dir / "addons" / TEST_ADDON_NAME
    (addon_dir / "disable").chmod(stat.S_IREAD)
    yield repo_dir


@contextmanager
def create_test_repo(repo_name: str):
    # Create temporary dummy test git repository
    addons = Path("/tmp/addons")
    os.mkdir(Path(addons))
    repo_dir = addons / repo_name
    os.mkdir(Path(repo_dir))

    # Create the .git file
    with open(repo_dir / ".git", mode="w+"):
        pass

    yield repo_dir

    # Cleanup
    shutil.rmtree(Path(addons))


@patch("addons.git_rollback")
@patch("addons.git_current_commit")
@patch("addons.subprocess")
@patch("addons.snap_common", return_value=Path("/tmp/"))
@patch("addons.validate_addons_repo", side_effect=AddonsYamlFormatError("foo"))
def test_update_rollbacks_repo_on_validation_error(
    validate_addons_repo_mock,
    snap_common_mock,
    subprocess_mock,
    git_current_commit_mock,
    git_rollback_mock,
):
    with create_test_repo("repo_to_update") as repo_dir:

        with pytest.raises(SystemExit):
            update.callback("repo_to_update", skip_check_root=True)

        validate_addons_repo_mock.assert_called_once_with(repo_dir)
        git_current_commit_mock.assert_called_once_with(repo_dir)
        git_rollback_mock.assert_called_once_with(git_current_commit_mock.return_value, repo_dir)
