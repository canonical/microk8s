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

import abc
import logging
import os
import pathlib
import requests
import shlex
import sys
from typing import Dict
from typing import Optional, Sequence

from . import errors
from ._multipass._instance_info import InstanceInfo

logger = logging.getLogger(__name__)


class Provider(abc.ABC):
    def __init__(
        self,
        *,
        echoer,
        is_ephemeral: bool = False,
        build_provider_flags: Dict[str, str] = None,
    ) -> None:
        self.echoer = echoer
        self._is_ephemeral = is_ephemeral

        self.instance_name = "microk8s-vm"

        if build_provider_flags is None:
            build_provider_flags = dict()
        self.build_provider_flags = build_provider_flags.copy()

        self._cached_home_directory: Optional[pathlib.Path] = None

    @classmethod
    def ensure_provider(cls) -> None:
        """Necessary steps to ensure the provider is correctly setup."""

    @classmethod
    def setup_provider(cls, *, echoer) -> None:
        """Necessary steps to install the provider on the host."""

    @classmethod
    def _get_provider_name(cls) -> str:
        """Return the provider name."""

    @classmethod
    def _get_is_snap_injection_capable(cls) -> bool:
        """Return whether the provider can install snaps from the host."""

    @abc.abstractmethod
    def create(self) -> None:
        """Provider steps needed to create a fully functioning environment."""

    @abc.abstractmethod
    def destroy(self) -> None:
        """Provider steps needed to ensure the instance is destroyed.

        This method should be safe to call multiple times and do nothing
        if the instance to destroy is already destroyed.
        """

    @abc.abstractmethod
    def get_instance_info(self) -> InstanceInfo:
        """Return the instance info."""

    @abc.abstractmethod
    def run(self, command: Sequence[str], hide_output: bool = False) -> Optional[bytes]:
        """Run a command on the instance."""

    @abc.abstractmethod
    def _launch(self, specs: Dict):
        """Launch the instance."""

    @abc.abstractmethod
    def _start(self):
        """Start an existing the instance."""

    @abc.abstractmethod
    def _push_file(self, *, source: str, destination: str) -> None:
        """Push a file into the instance."""

    @abc.abstractmethod
    def pull_file(self, name: str, destination: str, delete: bool = False) -> None:
        """
        Provider steps needed to retrieve a file from the instance, optionally
        deleting the source file after a successful retrieval.

        :param name: the remote filename.
        :type name: str
        :param destination: the local filename.
        :type destination: str
        :param delete: whether the file should be deleted.
        :type delete: bool
        """

    @abc.abstractmethod
    def shell(self) -> None:
        """Provider steps to provide a shell into the instance."""

    def launch_instance(self, specs: Dict) -> None:
        try:
            # An ProviderStartError exception here means we need to create.
            self._start()
        except errors.ProviderInstanceNotFoundError:
            self._launch(specs)
            self._check_connectivity()
            # We need to setup MicroK8s and scan for cli commands.
            self._setup_microk8s(specs)
            self._copy_kubeconfig_to_kubectl(specs)

    def _check_connectivity(self) -> None:
        """Check that the VM can access the internet."""
        try:
            requests.get("https://snapcraft.io")
        except requests.exceptions.RequestException:
            self.destroy()
            url = None
            if sys.platform == "win32":
                url = "https://multipass.run/docs/troubleshooting-networking-on-windows"
            elif sys.platform == "darwin":
                url = "https://multipass.run/docs/troubleshooting-networking-on-macos"

            if url:
                raise errors.ConnectivityError(
                    "The VM cannot connect to snapcraft.io, please see {}".format(url)
                )
            else:
                raise

    def _copy_kubeconfig_to_kubectl(self, specs: Dict):
        kubeconfig_path = specs.get("kubeconfig")
        kubeconfig = self.run(command=["microk8s", "config"], hide_output=True)

        if not os.path.isdir(os.path.dirname(kubeconfig_path)):
            os.mkdir(os.path.dirname(kubeconfig_path))

        with open(kubeconfig_path, "wb") as f:
            f.write(kubeconfig)

    def _setup_microk8s(self, specs: Dict) -> None:
        self.run("snap install microk8s --classic --channel {}".format(specs["channel"]).split())
        if sys.platform == "win32":
            self.run("snap install microk8s-integrator-windows".split())
        elif sys.platform == "darwin":
            self.run("snap install microk8s-integrator-macos".split())

    def _get_env_command(self) -> Sequence[str]:
        """Get command sequence for `env` with configured flags."""

        env_list = ["env"]

        # Pass through configurable environment variables.
        for key in ["http_proxy", "https_proxy"]:
            value = self.build_provider_flags.get(key)
            if not value:
                continue

            # Ensure item is treated as string and append it.
            value = str(value)
            env_list.append(f"{key}={value}")

        return env_list

    def _get_home_directory(self) -> pathlib.Path:
        """Get user's home directory path."""
        if self._cached_home_directory is not None:
            return self._cached_home_directory

        command = ["printenv", "HOME"]
        run_output = self.run(command=command, hide_output=True)

        # Shouldn't happen, but due to _run()'s return type as being Optional,
        # we need to check for it anyways for mypy.
        if not run_output:
            provider_name = self._get_provider_name()
            raise errors.ProviderExecError(
                provider_name=provider_name, command=command, exit_code=2
            )

        cached_home_directory = pathlib.Path(run_output.decode().strip())

        self._cached_home_directory = cached_home_directory
        return cached_home_directory

    def _base_has_changed(self, base: str, provider_base: str) -> bool:
        # Make it backwards compatible with instances without project info
        if base == "core18" and provider_base is None:
            return False
        elif base != provider_base:
            return True

        return False

    def _log_run(self, command: Sequence[str]) -> None:
        cmd_string = " ".join([shlex.quote(c) for c in command])
        logger.debug(f"Running: {cmd_string}")

    @abc.abstractmethod
    def stop(self) -> None:
        pass
