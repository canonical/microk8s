# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2018 Canonical Ltd
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
import shutil
import subprocess

from time import sleep
from typing import Dict, Optional, Sequence  # noqa: F401

from ._windows import windows_reload_multipass_path_env, windows_install_multipass

from vm_providers import errors
from vm_providers.repo.snaps import install_snaps

logger = logging.getLogger(__name__)


def _run(command: Sequence[str], stdin=subprocess.DEVNULL) -> None:
    logger.debug("Running {}".format(" ".join(command)))
    subprocess.check_call(command, stdin=stdin)


def _run_output(command: Sequence[str], **kwargs) -> bytes:
    logger.debug("Running {}".format(" ".join(command)))
    return subprocess.check_output(command, **kwargs)


class MultipassCommand:
    """An object representation of common multipass cli commands."""

    provider_name = "multipass"
    provider_cmd = "multipass"

    @classmethod
    def ensure_multipass(cls, platform: str) -> None:
        if platform == "win32":
            # Reload path env just in case multipass was installed without
            # launching a new command prompt / shell.
            windows_reload_multipass_path_env()

        if shutil.which(cls.provider_cmd):
            return

        if platform == "darwin":
            prompt_installable = True
        elif platform == "linux" and shutil.which("snap"):
            prompt_installable = True
        elif platform == "win32":
            prompt_installable = True
        else:
            prompt_installable = False

        raise errors.ProviderNotFound(
            provider=cls.provider_name,
            prompt_installable=prompt_installable,
            error_message="https://multipass.run",
        )

    @classmethod
    def _wait_for_multipass_ready(cls, *, echoer):
        echoer.wrapped("Waiting for multipass...")
        retry_count = 60
        while retry_count:
            try:
                output = subprocess.check_output([cls.provider_cmd, "version"]).decode()
            except subprocess.CalledProcessError:
                output = ""
            except FileNotFoundError:
                raise errors.ProviderStartError(
                    provider_name=cls.provider_name,
                    error_message="multipass not found - please check that it"
                    " can be found in the configured PATH",
                )

            # if multipassd is in the version information, it means the service is up
            # and we can carry on
            if "multipassd" in output:
                break

            retry_count -= 1
            sleep(1)

        # No need to worry about getting to this point by exhausting our retry count,
        # the rest of the stack will handle the error appropriately.

    @classmethod
    def setup_multipass(cls, *, echoer, platform: str) -> None:
        if platform == "linux":
            install_snaps(["multipass/latest/stable"])
        elif platform == "darwin":
            try:
                subprocess.check_call(["brew", "install", "multipass", "--cask"])
            except subprocess.CalledProcessError:
                raise errors.ProviderStartError(
                    provider_name=cls.provider_name,
                    error_message="Failed to install multipass using homebrew.\n"
                    "Verify your homebrew installation and try again.\n"
                    "Alternatively, manually install multipass by running"
                    " 'brew install multipass --cask'.",
                )
        elif platform == "win32":
            windows_install_multipass(echoer)
        else:
            raise EnvironmentError(
                "Setting up multipass for {!r} is not supported.".format(platform)
            )

        # wait for multipassd to be available
        cls._wait_for_multipass_ready(echoer=echoer)

    def __init__(self, *, platform: str) -> None:
        """Initialize a MultipassCommand instance.

        :raises errors.ProviderCommandNotFound:
            if the multipass command is not found.
        """
        self.ensure_multipass(platform=platform)

    def launch(
        self,
        *,
        instance_name: str,
        image: str,
        cpus: str = None,
        mem: str = None,
        disk: str = None,
        remote: str = None,
        cloud_init: str = None
    ) -> None:
        """Passthrough for running multipass launch.

        :param str instance_name: the name the launched instance will have.
        :param str image: the image to create the instance with.
        :param str cpus: amount of virtual CPUs to assign to the launched instance.
        :param str mem: amount of RAM to assign to the launched instance.
        :param str disk: amount of disk space the instance will see.
        :param str remote: the remote server to retrieve the image from.
        :param str cloud_init: path to a user-data cloud-init configuration.
        """
        if remote is not None:
            image = "{}:{}".format(remote, image)
        cmd = [self.provider_cmd, "launch", image, "--name", instance_name]
        if cloud_init is not None:
            cmd.extend(["--cloud-init", cloud_init])
        if cpus is not None:
            cmd.extend(["--cpus", cpus])
        if mem is not None:
            cmd.extend(["--memory", mem])
        if disk is not None:
            cmd.extend(["--disk", disk])
        try:
            _run(cmd)
        except subprocess.CalledProcessError as process_error:
            raise errors.ProviderLaunchError(
                provider_name=self.provider_name, exit_code=process_error.returncode
            ) from process_error

    def start(self, *, instance_name: str) -> None:
        """Passthrough for running multipass start.

        :param str instance_name: the name of the instance to start.
        """
        cmd = [self.provider_cmd, "start", instance_name]
        try:
            _run(cmd)
        except subprocess.CalledProcessError as process_error:
            raise errors.ProviderStartError(
                provider_name=self.provider_name, exit_code=process_error.returncode
            ) from process_error

    def stop(self, *, instance_name: str, time: int = None) -> None:
        """Passthrough for running multipass stop.

        :param str instance_name: the name of the instance to stop.
        :param str time: time from now, in minutes, to delay shutdown of the
                         instance.
        """
        cmd = [self.provider_cmd, "stop"]
        if time:
            cmd.extend(["--time", str(time)])
        cmd.append(instance_name)
        try:
            _run(cmd)
        except subprocess.CalledProcessError as process_error:
            raise errors.ProviderStopError(
                provider_name=self.provider_name, exit_code=process_error.returncode
            ) from process_error

    def delete(self, *, instance_name: str, purge=True) -> None:
        """Passthrough for running multipass delete.

        :param str instance_name: the name of the instance to delete.
        :param bool purge: if true, purge the instance's image after deleting.
        """
        cmd = [self.provider_cmd, "delete", instance_name]
        if purge:
            cmd.append("--purge")
        try:
            _run(cmd)
        except subprocess.CalledProcessError as process_error:
            raise errors.ProviderDeleteError(
                provider_name=self.provider_name, exit_code=process_error.returncode
            ) from process_error

    def execute(
        self, *, command: Sequence[str], instance_name: str, hide_output: bool = False
    ) -> Optional[bytes]:
        """Passthrough for running multipass exec.

        :param list command: the command to execute on the instance.
        :param str instance_name: the name of the instance to execute command.
        :param bool hide_output: hide the output from stdout.
        """
        cmd = [self.provider_cmd, "exec", instance_name, "--"] + list(command)
        output = None
        try:
            if hide_output:
                output = _run_output(cmd)
            else:
                _run(cmd, stdin=None)
        except subprocess.CalledProcessError as process_error:
            raise errors.ProviderExecError(
                provider_name=self.provider_name,
                command=command,
                exit_code=process_error.returncode,
            ) from process_error

        return output

    def shell(self, *, instance_name: str) -> None:
        """Passthrough for running multipass shell.

        :param str instance_name: the name of the instance to execute command.
        """
        try:
            _run([self.provider_cmd, "shell", instance_name])
        except subprocess.CalledProcessError as process_error:
            raise errors.ProviderShellError(
                provider_name=self.provider_name, exit_code=process_error.returncode
            ) from process_error

    def mount(
        self,
        *,
        source: str,
        target: str,
        uid_map: Dict[str, str] = None,
        gid_map: Dict[str, str] = None
    ) -> None:
        """Passthrough for running multipass mount.

        :param str source: path to the local directory to mount.
        :param str target: mountpoint inside the instance in the form of
                           <instance-name>:path.
        :param dict uid_map: A mapping of user IDs for use in the mount of the form
                             <host-id> -> <instance-id>.
                             File and folder ownership will be mapped from
                             <host> to <instance-name> inside the instance.
        :param dict gid_map: A mapping of group IDs for use in the mount of the form
                             <host-id> -> <instance-id>.
                             File and folder ownership will be mapped from
                             <host> to <instance-name> inside the instance.
        :raises errors.ProviderMountError: when the mount operation fails.
        """
        cmd = [self.provider_cmd, "mount", source, target]
        if uid_map is None:
            uid_map = dict()
        for host_map, instance_map in uid_map.items():
            cmd.extend(["--uid-map", "{}:{}".format(host_map, instance_map)])
        if gid_map is None:
            gid_map = dict()
        for host_map, instance_map in gid_map.items():
            cmd.extend(["--gid-map", "{}:{}".format(host_map, instance_map)])
        try:
            _run(cmd)
        except subprocess.CalledProcessError as process_error:
            raise errors.ProviderMountError(
                provider_name=self.provider_name, exit_code=process_error.returncode
            ) from process_error

    def umount(self, *, mount: str) -> None:
        """Passthrough for running multipass mount.

        :param str mount: mountpoint inside the instance in the form of
                           <instance-name>:path to unmount.
        :raises errors.ProviderUMountError: when the unmount operation fails.
        """
        cmd = [self.provider_cmd, "umount", mount]
        try:
            _run(cmd)
        except subprocess.CalledProcessError as process_error:
            raise errors.ProviderUnMountError(
                provider_name=self.provider_name, exit_code=process_error.returncode
            ) from process_error

    def copy_files(self, *, source: str, destination: str) -> None:
        """Passthrough for running multipass copy-files.

        :param str source: the source file to copy, using syntax expected
                           by multipass.
        :param str destination: the destination of the copied file, using
                                syntax expected by multipass.
        """
        cmd = [self.provider_cmd, "copy-files", source, destination]
        try:
            _run(cmd)
        except subprocess.CalledProcessError as process_error:
            raise errors.ProviderFileCopyError(
                provider_name=self.provider_name, exit_code=process_error.returncode
            ) from process_error

    def info(self, *, instance_name: str, output_format: str = None) -> bytes:
        """Passthrough for running multipass info."""
        cmd = [self.provider_cmd, "info", instance_name]
        if output_format is not None:
            cmd.extend(["--format", output_format])
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise errors.ProviderInfoError(
                provider_name=self.provider_name,
                exit_code=process.returncode,
                stderr=stderr,
            )
        return stdout
