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
import sys
from typing import Dict, Optional, Sequence

from time import sleep
from vm_providers import errors
from .._base_provider import Provider
from ._instance_info import InstanceInfo
from ._multipass_command import MultipassCommand

logger = logging.getLogger(__name__)


class Multipass(Provider):
    """A multipass provider for MicroK8s to execute its lifecycle."""

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

    def run(self, command: Sequence[str], hide_output: bool = False) -> Optional[bytes]:
        cmd = ["sudo"]
        cmd.extend(command)
        self._log_run(cmd)

        return self._multipass_cmd.execute(
            instance_name=self.instance_name, command=cmd, hide_output=hide_output
        )

    def _launch(self, specs: Dict) -> None:

        # prepare core launch setting
        image = specs["image"]
        cpus = "{}".format(specs["cpu"])
        mem = "{}G".format(specs["mem"])
        disk = "{}G".format(specs["disk"])

        try_for = 10

        while True:
            try:
                self._multipass_cmd.launch(
                    instance_name=self.instance_name, cpus=cpus, mem=mem, disk=disk, image=image
                )
            except Exception:
                if try_for > 0:
                    try_for -= 1
                    sleep(1)
                    continue
                else:
                    raise
            else:
                break

    def get_instance_info(self) -> InstanceInfo:
        try:
            instance_info = self._get_instance_info()
            return instance_info
        except errors.ProviderInfoError as instance_error:
            # Until we have proper multipass error codes to know if this
            # was a communication error we should keep this error tracking
            # and generation here.
            raise errors.ProviderInstanceNotFoundError(
                instance_name=self.instance_name
            ) from instance_error

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

    def create(self, specs: Dict) -> None:
        """Create the multipass instance and setup the build environment."""
        self.echoer.info("Launching a VM.")
        self.launch_instance(specs)
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
        self.run(command=["test", "-f", name])

        # copy file from instance
        source = "{}:{}".format(self.instance_name, name)
        self._multipass_cmd.copy_files(source=source, destination=destination)
        if delete:
            self.run(command=["rm", name])

    def shell(self) -> None:
        self.run(command=["/bin/bash"])

    def _get_instance_info(self) -> InstanceInfo:
        instance_info_raw = self._multipass_cmd.info(
            instance_name=self.instance_name, output_format="json"
        )
        return InstanceInfo.from_json(
            instance_name=self.instance_name, json_info=instance_info_raw.decode()
        )

    def start(self) -> None:
        instance_info = self._instance_info = self._get_instance_info()
        if not instance_info.is_stopped():
            return

        self._multipass_cmd.start(instance_name=self.instance_name)

    def stop(self) -> None:
        instance_info = self._instance_info = self._get_instance_info()
        if instance_info.is_stopped():
            return

        self._multipass_cmd.stop(instance_name=self.instance_name)
