# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2017-2019 Canonical Ltd
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
import logging
import os
import sys
from subprocess import check_call, check_output, CalledProcessError
from typing import List, Sequence, Set, Union
from urllib import parse

import requests_unixsocket
from requests import exceptions

from . import errors


_STORE_ASSERTION = [
    "account-key",
    "public-key-sha3-384=BWDEoaqyr25nF5SNCvEv2v7QnM9QsfCc0PBMYD_i2NGSQ32EF2d4D0hqUel3m8ul",
]

_CHANNEL_RISKS = ["stable", "candidate", "beta", "edge"]
logger = logging.getLogger(__name__)


class SnapPackage:
    """SnapPackage acts as a mediator to install or refresh a snap.

    It uses information provided by snapd implicitly referring to the local
    and remote stores to obtain information about the snap, such as its
    confinement value and channel availability.

    This information can also be used to determine if a snap should be
    installed or refreshed.

    There are risks of the data falling out of date between the query and the
    requested action given that it is not possible to hold a global lock on
    snapd and the store data can change in between validation and execution.
    """

    @classmethod
    def is_valid_snap(cls, snap):
        return cls(snap).is_valid()

    @classmethod
    def is_snap_installed(cls, snap):
        return cls(snap).installed

    def __init__(self, snap):
        """Lifecycle handler for a snap of the format <snap-name>/<channel>."""
        self.name, self.channel = _get_parsed_snap(snap)
        self._original_channel = self.channel
        if not self.channel or self.channel == "stable":
            self.channel = "latest/stable"

        # This store information from a local request
        self._local_snap_info = None
        # And this stores information from a remote request
        self._store_snap_info = None

        self._is_installed = None
        self._is_in_store = None

    @property
    def installed(self):
        if self._is_installed is None:
            self._is_installed = self.get_local_snap_info() is not None
        return self._is_installed

    @property
    def in_store(self):
        if self._is_in_store is None:
            try:
                self._is_in_store = self.get_store_snap_info() is not None
            except errors.SnapUnavailableError:
                self._is_in_store = False
        return self._is_in_store

    def get_local_snap_info(self):
        """Returns a local payload for the snap.

        Validity of the results are determined by checking self.installed."""
        if self._is_installed is None:
            with contextlib.suppress(exceptions.HTTPError):
                self._local_snap_info = _get_local_snap_info(self.name)
        return self._local_snap_info

    def get_store_snap_info(self):
        """Returns a store payload for the snap."""
        if self._is_in_store is None:
            # Some environments timeout often, like the armv7 testing
            # infrastructure. Given that constraint, we add some retry
            # logic.
            retry_count = 5
            while retry_count > 0:
                try:
                    self._store_snap_info = _get_store_snap_info(self.name)
                    break
                except exceptions.HTTPError as http_error:
                    logger.debug(
                        "The http error when checking the store for "
                        "{!r} is {!r} (retries left {})".format(
                            self.name, http_error.response.status_code, retry_count
                        )
                    )
                    if http_error.response.status_code == 404:
                        raise errors.SnapUnavailableError(
                            snap_name=self.name, snap_channel=self.channel
                        )
                    retry_count -= 1

        return self._store_snap_info

    def _get_store_channels(self):
        snap_store_info = self.get_store_snap_info()
        if not self.in_store:
            return dict()

        return snap_store_info["channels"]

    def get_current_channel(self):
        current_channel = ""
        if self.installed:
            local_snap_info = self.get_local_snap_info()
            current_channel = local_snap_info["channel"]
            if any([current_channel.startswith(risk) for risk in _CHANNEL_RISKS]):
                current_channel = "latest/{}".format(current_channel)
        return current_channel

    def has_assertions(self) -> bool:
        # A revision starting with x has been installed with
        # --dangerous.
        return not self.get_local_snap_info()["revision"].startswith("x")

    def is_classic(self) -> bool:
        store_channels = self._get_store_channels()
        try:
            return store_channels[self.channel]["confinement"] == "classic"
        except KeyError:
            # We have seen some KeyError issues when running tests that are
            # hard to debug as they only occur there, logging in debug mode
            # will help uncover the root cause if it happens again.
            logger.debug(
                "Current store channels are {!r} and the store"
                "payload is {!r}".format(store_channels, self._store_snap_info)
            )
            raise

    def is_valid(self) -> bool:
        """Check if the snap is valid."""
        if not self.in_store:
            return False
        store_channels = self._get_store_channels()
        return self.channel in store_channels.keys()

    def local_download(self, *, snap_path: str, assertion_path: str) -> None:
        assertions = list()  # type: List[List[str]]
        # We write an empty assertions file for dangerous installs to
        # have a consistent interface.
        if self.has_assertions():
            assertions.append(["snap-declaration", "snap-name={}".format(self.name)])
            assertions.append(
                [
                    "snap-revision",
                    "snap-revision={}".format(self._local_snap_info["revision"]),
                    "snap-id={}".format(self._local_snap_info["id"]),
                ]
            )

        if assertions:
            assertions.insert(0, _STORE_ASSERTION)

        with open(assertion_path, "wb") as assertion_file:
            for assertion in assertions:
                assertion_file.write(get_assertion(assertion))
                assertion_file.write(b"\n")

        snap_file_iter = _get_local_snap_file_iter(self.name, chunk_size=1024)
        with open(snap_path, "wb") as snap_file:
            for buf in snap_file_iter:
                snap_file.write(buf)

    def download(self, *, directory: str = None):
        """Downloads a given snap."""
        # We use the `snap download` command here on recommendation
        # of the snapd team.
        snap_download_cmd = ["snap", "download", self.name]
        if self._original_channel:
            snap_download_cmd.extend(["--channel", self._original_channel])
        try:
            check_output(snap_download_cmd, cwd=directory)
        except CalledProcessError:
            raise errors.SnapDownloadError(snap_name=self.name, snap_channel=self.channel)

    def install(self):
        """Installs the snap onto the system."""
        if not self.is_valid():
            raise errors.SnapUnavailableError(snap_name=self.name, snap_channel=self.channel)

        snap_install_cmd = []
        if _snap_command_requires_sudo():
            snap_install_cmd = ["sudo"]
        snap_install_cmd.extend(["snap", "install", self.name])
        if self._original_channel:
            snap_install_cmd.extend(["--channel", self._original_channel])
        if self.is_classic():
            # TODO make this a user explicit choice
            snap_install_cmd.append("--classic")
        try:
            check_call(snap_install_cmd)
        except CalledProcessError:
            raise errors.SnapInstallError(snap_name=self.name, snap_channel=self.channel)

        # Now that the snap is installed, invalidate the data we had on it.
        self._is_installed = None

    def refresh(self):
        """Refreshes a snap onto a channel on the system."""
        if not self.is_valid():
            raise errors.SnapUnavailableError(snap_name=self.name, snap_channel=self.channel)

        snap_refresh_cmd = []
        if _snap_command_requires_sudo():
            snap_refresh_cmd = ["sudo"]
        snap_refresh_cmd.extend(["snap", "refresh", self.name, "--channel", self.channel])
        if self.is_classic():
            # TODO make this a user explicit choice
            snap_refresh_cmd.append("--classic")
        try:
            check_call(snap_refresh_cmd)
        except CalledProcessError:
            raise errors.SnapRefreshError(snap_name=self.name, snap_channel=self.channel)

        # Now that the snap is refreshed, invalidate the data we had on it.
        self._is_installed = None


def download_snaps(*, snaps_list: Sequence[str], directory: str) -> None:
    """
    Download snaps of the format <snap-name>/<channel> into directory.

    The target directory is created if it does not exist.
    """
    # TODO manifest.yaml with snap revision from future machine output
    # for `snap download`.
    os.makedirs(directory, exist_ok=True)
    for snap in snaps_list:
        snap_pkg = SnapPackage(snap)
        if not snap_pkg.is_valid():
            raise errors.SnapUnavailableError(
                snap_name=snap_pkg.name, snap_channel=snap_pkg.channel
            )

        # TODO: use dependency injected echoer
        logger.info("Downloading snap {!r}".format(snap_pkg.name))
        snap_pkg.download(directory=directory)


def install_snaps(snaps_list: Union[Sequence[str], Set[str]]) -> List[str]:
    """Install snaps of the format <snap-name>/<channel>.

    :return: a list of "name=revision" for the snaps installed.
    """
    snaps_installed = []
    for snap in snaps_list:
        snap_pkg = SnapPackage(snap)

        # Allow bases to be installed from non stable channels.
        snap_pkg_channel = snap_pkg.get_store_snap_info()["channel"]
        snap_pkg_type = snap_pkg.get_store_snap_info()["type"]
        if snap_pkg_channel != "stable" and snap_pkg_type == "base":
            snap_pkg = SnapPackage(
                "{snap_name}/latest/{channel}".format(
                    snap_name=snap_pkg.name, channel=snap_pkg_channel
                )
            )

        if not snap_pkg.installed:
            snap_pkg.install()
        elif snap_pkg.get_current_channel() != snap_pkg.channel:
            snap_pkg.refresh()

        snaps_installed.append(
            "{}={}".format(snap_pkg.name, snap_pkg.get_local_snap_info()["revision"])
        )
    return snaps_installed


def _snap_command_requires_sudo():
    # snap whoami returns - if the user is not logged in.
    output = check_output(["snap", "whoami"])
    whoami = output.decode(sys.getfilesystemencoding())
    try:
        requires_root = whoami.split(":")[1].strip() == "-"
    # A safeguard if the output changes
    except IndexError:
        requires_root = True
    if requires_root:
        logger.warning("snapd is not logged in, snap install commands will use sudo")
    return requires_root


def get_assertion(assertion_params: Sequence[str]) -> bytes:
    """Get assertion information.

    :param assertion_params: a sequence of strings to pass to 'snap known'.
    :returns: a stream of bytes from the assertion.
    :rtype: bytes
    """
    try:
        return check_output(["snap", "known", *assertion_params])
    except CalledProcessError as call_error:
        raise errors.SnapGetAssertionError(assertion_params=assertion_params) from call_error


def _get_parsed_snap(snap):
    if "/" in snap:
        sep_index = snap.find("/")
        snap_name = snap[:sep_index]
        snap_channel = snap[sep_index + 1 :]
    else:
        snap_name = snap
        snap_channel = ""
    return snap_name, snap_channel


def get_snapd_socket_path_template():
    return "http+unix://%2Frun%2Fsnapd.socket/v2/{}"


def _get_local_snap_file_iter(snap_name, *, chunk_size: int):
    slug = "snaps/{}/file".format(parse.quote(snap_name, safe=""))
    url = get_snapd_socket_path_template().format(slug)
    try:
        snap_file = requests_unixsocket.get(url)
    except exceptions.ConnectionError as e:
        raise errors.SnapdConnectionError(snap_name, url) from e
    snap_file.raise_for_status()
    return snap_file.iter_content(chunk_size)


def _get_local_snap_info(snap_name):
    slug = "snaps/{}".format(parse.quote(snap_name, safe=""))
    url = get_snapd_socket_path_template().format(slug)
    try:
        snap_info = requests_unixsocket.get(url)
    except exceptions.ConnectionError as e:
        raise errors.SnapdConnectionError(snap_name, url) from e
    snap_info.raise_for_status()
    return snap_info.json()["result"]


def _get_store_snap_info(snap_name):
    # This logic uses /v2/find returns an array of results, given that
    # we do a strict search either 1 result or a 404 will be returned.
    slug = "find?{}".format(parse.urlencode(dict(name=snap_name)))
    url = get_snapd_socket_path_template().format(slug)
    snap_info = requests_unixsocket.get(url)
    snap_info.raise_for_status()
    return snap_info.json()["result"][0]


def get_installed_snaps():
    """Return all the snaps installed in the system.

    :return: a list of "name=revision" for the snaps installed.
    """
    slug = "snaps"
    url = get_snapd_socket_path_template().format(slug)
    try:
        snap_info = requests_unixsocket.get(url)
        snap_info.raise_for_status()
        local_snaps = snap_info.json()["result"]
    except exceptions.ConnectionError:
        local_snaps = []
    return ["{}={}".format(snap["name"], snap["revision"]) for snap in local_snaps]
