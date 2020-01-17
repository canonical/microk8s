# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2018-2019 Canonical Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import contextlib
import datetime
import enum
import logging
import os
from typing import Callable, List, Optional
from typing import Any, Dict  # noqa: F401

from . import errors
from snapcraft import storeapi, yaml_utils
from snapcraft.internal import repo

logger = logging.getLogger(__name__)


class _SnapOp(enum.Enum):
    NOP = 0
    INJECT = 1
    INSTALL = 2
    REFRESH = 3


def _get_snap_channel(snap_name: str) -> storeapi.channels.Channel:
    """Returns the channel to use for snap_name."""
    env_channel = os.getenv("SNAPCRAFT_BUILD_ENVIRONMENT_CHANNEL_SNAPCRAFT", None)
    if env_channel is not None and snap_name == "snapcraft":
        channel = env_channel
        logger.warning(
            "SNAPCRAFT_BUILD_ENVIRONMENT_CHANNEL_SNAPCRAFT is set: installing "
            "snapcraft from {}".format(channel)
        )
    else:
        channel = "latest/stable"

    return storeapi.channels.Channel(channel)


class _SnapManager:
    def __init__(
        self,
        *,
        snap_name: str,
        remote_snap_dir: str,
        latest_revision: Optional[str],
        snap_arch: str,
        inject_from_host: bool = True
    ) -> None:
        self.snap_name = snap_name
        self._remote_snap_dir = remote_snap_dir
        self._snap_arch = snap_arch
        self._inject_from_host = inject_from_host

        self._latest_revision = latest_revision
        self.__required_operation = None  # type: Optional[_SnapOp]
        self.__repo = None  # type: Optional[repo.snaps.SnapPackage]
        self.__revision = None  # type: Optional[str]
        self.__install_cmd = None  # type: Optional[List[str]]
        self.__assertion_ack_cmd = None  # type: Optional[List[str]]

    def _get_snap_repo(self):
        if self.__repo is None:
            self.__repo = repo.snaps.SnapPackage(self.snap_name)
        return self.__repo

    def get_op(self) -> _SnapOp:
        if self.__required_operation is not None:
            return self.__required_operation

        # From the point of view of multiple architectures if the target host (this)
        # is different than that of where these snaps run from, then we always need to
        # install from the store
        if self._inject_from_host:
            # Get information from the host.
            host_snap_repo = self._get_snap_repo()
            try:
                host_snap_info = host_snap_repo.get_local_snap_info()
                is_installed = host_snap_repo.installed
            except repo.errors.SnapdConnectionError:
                # This maybe because we are in a docker instance or another OS.
                is_installed = False
        else:
            is_installed = False

        # The evaluations for the required operation is as follows:
        # - if the snap is not installed on the host (is_installed == False),
        #   and the snap is not installed in the build environment
        #   (_latest_revision is None), then a store install will take place.
        # - else if the snap is not installed on the host (is_installed == False),
        #   but the is previously installed revision in the build environment
        #   (_latest_revision is not None), then a store install will take place.
        # - else if the snap is installed on the host (is_installed == True),
        #   and the snap installed in the build environment (_latest_revision) matches
        #   the one on the host, no operation takes place.
        # - else if the snap is installed on the host (is_installed == True),
        #   and the snap installed in the build environment (_latest_revision) does not
        #   match the one on the host, then a snap injection from the host will take place.
        if not is_installed and self._latest_revision is None:
            op = _SnapOp.INSTALL
        elif not is_installed and self._latest_revision is not None:
            op = _SnapOp.REFRESH
        elif is_installed and self._latest_revision == host_snap_info["revision"]:
            op = _SnapOp.NOP
        elif is_installed and self._latest_revision != host_snap_info["revision"]:
            op = _SnapOp.INJECT
        else:
            # This is a programmatic error
            raise RuntimeError(
                "Unhandled scenario for {!r} (host installed: {}, latest_revision {})".format(
                    self.snap_name, is_installed, self._latest_revision
                )
            )

        self.__required_operation = op
        return op


    def _set_data(self) -> None:
        op = self.get_op()
        host_snap_repo = self._get_snap_repo()

        install_cmd = list()  # type: List[str]
        assertion_ack_cmd = list()  # type: List[str]
        snap_revision = None

        if op == _SnapOp.INJECT:
            install_cmd = ["snap", "install"]
            host_snap_info = host_snap_repo.get_local_snap_info()
            snap_revision = host_snap_info["revision"]

            if snap_revision.startswith("x"):
                install_cmd.append("--dangerous")

            if host_snap_info["confinement"] == "classic":
                install_cmd.append("--classic")

            # File names need to be the last items in these two.
            install_cmd.append(
                os.path.join(
                    self._remote_snap_dir, "{}.snap".format(host_snap_repo.name)
                )
            )
            assertion_ack_cmd = [
                "snap",
                "ack",
                os.path.join(
                    self._remote_snap_dir, "{}.assert".format(host_snap_repo.name)
                ),
            ]

        elif op == _SnapOp.INSTALL or op == _SnapOp.REFRESH:
            install_cmd = ["snap", op.name.lower()]
            snap_channel = _get_snap_channel(self.snap_name)
            store_snap_info = storeapi.StoreClient().cpi.get_info(self.snap_name)
            snap_channel_map = store_snap_info.get_channel_mapping(
                risk=snap_channel.risk, track=snap_channel.track, arch=self._snap_arch
            )
            snap_revision = snap_channel_map.revision
            if snap_channel_map.confinement == "classic":
                install_cmd.append("--classic")
            install_cmd.extend(["--channel", snap_channel_map.channel_details.name])
            install_cmd.append(host_snap_repo.name)

        self.__install_cmd = install_cmd
        self.__assertion_ack_cmd = assertion_ack_cmd
        self.__revision = snap_revision

    def get_revision(self) -> str:
        if self.__revision is None:
            self._set_data()

        # Shouldn't happen - assert for sanity and mypy checking.
        if self.__revision is None:
            # Shouldn't happen.
            raise RuntimeError(
                "Unhandled scenario for {!r} (revision {})".format(
                    self.snap_name, self.__revision
                )
            )

        return self.__revision

    def get_snap_install_cmd(self) -> List[str]:
        if self.__install_cmd is None:
            self._set_data()

        # Shouldn't happen - assert for sanity and mypy checking.
        if self.__install_cmd is None:
            raise RuntimeError(
                "Unhandled scenario for {!r} (install_cmd {})".format(
                    self.snap_name, self.__install_cmd
                )
            )

        return self.__install_cmd

    def get_assertion_ack_cmd(self) -> List[str]:
        if self.__assertion_ack_cmd is None:
            self._set_data()

        # Shouldn't happen - assert for sanity and mypy checking.
        if self.__assertion_ack_cmd is None:
            raise RuntimeError(
                "Unhandled scenario for {!r} (assertion_ack_cmd {})".format(
                    self.snap_name, self.__assertion_ack_cmd
                )
            )

        return self.__assertion_ack_cmd


def _load_registry(registry_filepath: Optional[str]) -> Dict[str, List[Any]]:
    if registry_filepath is None or not os.path.exists(registry_filepath):
        return dict()

    with open(registry_filepath) as registry_file:
        return yaml_utils.load(registry_file)


def _save_registry(
    registry_data: Dict[str, List[Any]], registry_filepath: Optional[str]
) -> None:
    if registry_filepath is None:
        return

    dirpath = os.path.dirname(registry_filepath)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)

    with open(registry_filepath, "w") as registry_file:
        yaml_utils.dump(registry_data, stream=registry_file)


class SnapInjector:
    """Handle the process of adding snaps into the build environment.

    The specific knowledge of the build environment where these snaps will
    be injected is not required, instead runnables to execute the required
    operations against the build environment are provided upon initialization.

    The snaps to install or refresh in the build environment are added by calling
    add and finally applied by calling apply. If an operation is required, the
    revision that eventually made it into the environment is recorded in the
    registry.
    """

    def __init__(
        self,
        *,
        registry_filepath: str,
        snap_arch: str,
        runner: Callable[..., Optional[bytes]],
        file_pusher: Callable[..., None],
        inject_from_host: bool = True
    ) -> None:
        """
        Initialize a SnapInjector instance.

        :param str snap_arch: the snap architecture of the snaps to inject.
        :param str registry_filepath: path to where recordings of previusly installed
                                      revisions of a snap can be queried and recorded.
        :param runner: a callable which can run commands in the build environment.
        :param file_pusher: a callable that can push file from the host into the build
                            environment.
        :param bool inject_from_host: whether to look for snaps on the host and inject them.
        """

        self._snaps = []  # type: List[_SnapManager]
        self._registry_filepath = registry_filepath
        self._snap_arch = snap_arch
        self._inject_from_host = inject_from_host
        self._runner = runner
        self._file_pusher = file_pusher

        self._registry_data = _load_registry(registry_filepath)
        self._remote_snap_dir = "/var/tmp"

    def _disable_and_wait_for_refreshes(self) -> None:
        # Disable autorefresh for 15 minutes,
        # https://github.com/snapcore/snapd/pull/5436/files
        now_plus_15 = datetime.datetime.now() + datetime.timedelta(minutes=15)
        logger.debug("Holding refreshes for snaps.")
        self._runner(
            ["snap", "set", "core", "refresh.hold={}Z".format(now_plus_15.isoformat())],
            hide_output=True,
        )
        # Auto refresh may have kicked in while setting the hold.
        logger.debug("Waiting for pending snap auto refreshes.")
        with contextlib.suppress(errors.ProviderExecError):
            self._runner(["snap", "watch", "--last=auto-refresh"], hide_output=True)

    def _enable_snapd_snap(self) -> None:
        # Required to not install the core snap when building using
        # other bases.
        logger.debug("Enable use of snapd snap.")
        self._runner(
            ["snap", "set", "system", "experimental.snapd-snap=true"], hide_output=True
        )

    def _get_latest_revision(self, snap_name) -> Optional[str]:
        try:
            return self._registry_data[snap_name][-1]["revision"]
        except (IndexError, KeyError):
            return None

    def _record_revision(self, snap_name: str, snap_revision: str) -> None:
        entry = dict(revision=snap_revision)

        if snap_name not in self._registry_data:
            self._registry_data[snap_name] = [entry]
        else:
            self._registry_data[snap_name].append(entry)

    def add(self, snap_name: str) -> None:
        self._snaps.append(
            _SnapManager(
                snap_name=snap_name,
                remote_snap_dir=self._remote_snap_dir,
                latest_revision=self._get_latest_revision(snap_name),
                snap_arch=self._snap_arch,
                inject_from_host=self._inject_from_host,
            )
        )
