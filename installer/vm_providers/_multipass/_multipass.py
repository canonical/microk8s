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

import logging
import os
import sys
from typing import Dict, Optional, Sequence

from vm_providers import errors
from .._base_provider import Provider
from ._instance_info import InstanceInfo
from ._multipass_command import MultipassCommand

logger = logging.getLogger(__name__)


class _MachineSetting:
    def __init__(self, *, envvar: str, default: str) -> None:
        self._default = default
        self._envvar = envvar

    def get_value(self):
        value = os.getenv(self._envvar, self._default)
        if value != self._default:
            logger.warning(
                "{!r} was set to {!r} in the environment. "
                "Changing the default allocation upon user request".format(
                    self._envvar, value
                )
            )
        return value


class Multipass(Provider):
    """A multipass provider for snapcraft to execute its lifecycle."""

    @classmethod
    def ensure_provider(cls):
        MultipassCommand.ensure_multipass(platform=sys.platform)

    @classmethod
    def setup_provider(cls, *, echoer) -> None:
        MultipassCommand.setup_multipass(echoer=echoer, platform=sys.platform)

    @classmethod
    def _get_is_snap_injection_capable(cls) -> bool:
        return True

    @classmethod
    def _get_provider_name(cls):
        return "multipass"

    def run(
        self, command: Sequence[str], hide_output: bool = False
    ) -> Optional[bytes]:
        env_command = self._get_env_command()

        cmd = ["sudo", "-i"]
        cmd.extend(env_command)
        cmd.extend(command)
        self._log_run(cmd)

        return self._multipass_cmd.execute(
            instance_name=self.instance_name, command=cmd, hide_output=hide_output
        )

    def _launch(self) -> None:
        image = "18.04"

        cpus = _MachineSetting(envvar="MICROK8S_CPU", default="2")
        mem = _MachineSetting(envvar="MICROK8S_MEMORY", default="4G")
        disk = _MachineSetting(
            envvar="MICROK8S_DISK", default="256G"
        )

        self._multipass_cmd.launch(
            instance_name=self.instance_name,
            cpus=cpus.get_value(),
            mem=mem.get_value(),
            disk=disk.get_value(),
            image=image
        )

    def _start(self):
        try:
            instance_info = self._get_instance_info()
            if not instance_info.is_running():
                self._multipass_cmd.start(instance_name=self.instance_name)

        except errors.ProviderInfoError as instance_error:
            # Until we have proper multipass error codes to know if this
            # was a communication error we should keep this error tracking
            # and generation here.
            raise errors.ProviderInstanceNotFoundError(
                instance_name=self.instance_name
            ) from instance_error

    def _umount(self, *, mountpoint: str) -> None:
        mount = "{}:{}".format(self.instance_name, mountpoint)
        self._multipass_cmd.umount(mount=mount)

    def _push_file(self, *, source: str, destination: str) -> None:
        destination = "{}:{}".format(self.instance_name, destination)
        self._multipass_cmd.copy_files(source=source, destination=destination)

    def __init__(
        self,
        *,
        echoer,
        is_ephemeral: bool = False,
        build_provider_flags: Dict[str, str] = None,
    ) -> None:
        super().__init__(
            echoer=echoer,
            is_ephemeral=is_ephemeral,
            build_provider_flags=build_provider_flags,
        )
        self._multipass_cmd = MultipassCommand(platform=sys.platform)
        self._instance_info: Optional[InstanceInfo] = None

    def create(self) -> None:
        """Create the multipass instance and setup the build environment."""
        self.echoer.info("Launching a VM.")
        self.launch_instance()
        self._instance_info = self._get_instance_info()

    def destroy(self) -> None:
        """Destroy the instance, trying to stop it first."""
        try:
            instance_info = self._instance_info = self._get_instance_info()
        except errors.ProviderInfoError:
            return

        if instance_info.is_stopped():
            return

        self._multipass_cmd.stop(instance_name=self.instance_name)
        self._multipass_cmd.delete(instance_name=self.instance_name, purge=True)

    def pull_file(self, name: str, destination: str, delete: bool = False) -> None:
        # TODO add instance check.

        # check if file exists in instance
        self._run(command=["test", "-f", name])

        # copy file from instance
        source = "{}:{}".format(self.instance_name, name)
        self._multipass_cmd.copy_files(source=source, destination=destination)
        if delete:
            self._run(command=["rm", name])

    def shell(self) -> None:
        self._run(command=["/bin/bash"])

    def _get_instance_info(self) -> InstanceInfo:
        instance_info_raw = self._multipass_cmd.info(
            instance_name=self.instance_name, output_format="json"
        )
        return InstanceInfo.from_json(
            instance_name=self.instance_name, json_info=instance_info_raw.decode()
        )
