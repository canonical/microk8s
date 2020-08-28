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

import shlex
from typing import Any, Dict, Optional
from typing import Sequence  # noqa: F401

from common.errors import BaseError


class ConnectivityError(BaseError):
    pass


class ProviderBaseError(BaseError):
    pass


class ProviderNotSupportedError(ProviderBaseError):

    fmt = (
        "The {provider!r} provider is not supported, please choose a "
        "different one and try again."
    )

    def __init__(self, *, provider: str) -> None:
        super().__init__(provider=provider)


class ProviderNotFound(ProviderBaseError):

    fmt = "You need {provider!r} set-up to build snaps: {error_message}."

    def __init__(self, *, provider: str, prompt_installable: bool, error_message: str) -> None:
        super().__init__(
            provider=provider,
            prompt_installable=prompt_installable,
            error_message=error_message,
        )
        self.prompt_installable = prompt_installable
        self.provider = provider


class _GenericProviderError(ProviderBaseError):

    _FMT_ERROR_MESSAGE_AND_EXIT_CODE = (
        "An error occurred with the instance when trying to {action} with "
        "{provider_name!r}: returned exit code {exit_code!r}: {error_message}.\n"
        "Ensure that {provider_name!r} is setup correctly and try again."
    )

    _FMT_ERROR_MESSAGE = (
        "An error occurred with the instance when trying to {action} with "
        "{provider_name!r}: {error_message}.\n"
        "Ensure that {provider_name!r} is setup correctly and try again."
    )

    _FMT_EXIT_CODE = (
        "An error occurred with the instance when trying to {action} with "
        "{provider_name!r}: returned exit code {exit_code!r}.\n"
        "Ensure that {provider_name!r} is setup correctly and try again."
    )

    def __init__(
        self,
        *,
        provider_name: str,
        action: str,
        error_message: Optional[str] = None,
        exit_code: Optional[int] = None
    ) -> None:
        if exit_code is not None and error_message is not None:
            fmt = self._FMT_ERROR_MESSAGE_AND_EXIT_CODE
        elif error_message:
            fmt = self._FMT_ERROR_MESSAGE
        elif exit_code:
            fmt = self._FMT_EXIT_CODE
        else:
            raise RuntimeError("error_message nor exit_code are set")

        self.fmt = fmt

        super().__init__(
            provider_name=provider_name,
            action=action,
            error_message=error_message,
            exit_code=exit_code,
        )


class ProviderCommunicationError(ProviderBaseError):

    fmt = (
        "An error occurred when trying to communicate with the "
        "{provider_name!r} provider: {message}."
    )

    def __init__(self, *, provider_name: str, message: str) -> None:
        super().__init__(provider_name=provider_name, message=message)


class ProviderLaunchError(_GenericProviderError):
    def __init__(
        self,
        *,
        provider_name: str,
        error_message: Optional[str] = None,
        exit_code: Optional[int] = None
    ) -> None:
        super().__init__(
            action="launch",
            provider_name=provider_name,
            error_message=error_message,
            exit_code=exit_code,
        )


class ProviderStartError(_GenericProviderError):
    def __init__(
        self,
        *,
        provider_name: str,
        error_message: Optional[str] = None,
        exit_code: Optional[int] = None
    ) -> None:
        super().__init__(
            action="start",
            provider_name=provider_name,
            error_message=error_message,
            exit_code=exit_code,
        )


class ProviderStopError(_GenericProviderError):
    def __init__(
        self,
        *,
        provider_name: str,
        error_message: Optional[str] = None,
        exit_code: Optional[int] = None
    ) -> None:
        super().__init__(
            action="stop",
            provider_name=provider_name,
            error_message=error_message,
            exit_code=exit_code,
        )


class ProviderDeleteError(_GenericProviderError):
    def __init__(
        self,
        *,
        provider_name: str,
        error_message: Optional[str] = None,
        exit_code: Optional[int] = None
    ) -> None:
        super().__init__(
            action="delete",
            provider_name=provider_name,
            error_message=error_message,
            exit_code=exit_code,
        )


class ProviderExecError(ProviderBaseError):

    fmt = (
        "An error occurred when trying to execute {command_string!r} with "
        "{provider_name!r}: returned exit code {exit_code!r}."
    )

    def __init__(self, *, provider_name: str, command: Sequence[str], exit_code: int) -> None:
        command_string = " ".join(shlex.quote(i) for i in command)
        super().__init__(
            provider_name=provider_name,
            command=command,
            command_string=command_string,
            exit_code=exit_code,
        )


class ProviderShellError(_GenericProviderError):
    def __init__(
        self,
        *,
        provider_name: str,
        error_message: Optional[str] = None,
        exit_code: Optional[int] = None
    ) -> None:
        super().__init__(
            action="shell",
            provider_name=provider_name,
            error_message=error_message,
            exit_code=exit_code,
        )


class ProviderMountError(_GenericProviderError):
    def __init__(
        self,
        *,
        provider_name: str,
        error_message: Optional[str] = None,
        exit_code: Optional[int] = None
    ) -> None:
        super().__init__(
            action="mount",
            provider_name=provider_name,
            error_message=error_message,
            exit_code=exit_code,
        )


class ProviderUnMountError(_GenericProviderError):
    def __init__(
        self,
        *,
        provider_name: str,
        error_message: Optional[str] = None,
        exit_code: Optional[int] = None
    ) -> None:
        super().__init__(
            action="unmount",
            provider_name=provider_name,
            error_message=error_message,
            exit_code=exit_code,
        )


class ProviderFileCopyError(_GenericProviderError):
    def __init__(
        self,
        *,
        provider_name: str,
        error_message: Optional[str] = None,
        exit_code: Optional[int] = None
    ) -> None:
        super().__init__(
            action="copy files",
            provider_name=provider_name,
            error_message=error_message,
            exit_code=exit_code,
        )


class ProviderInfoError(ProviderBaseError):

    fmt = (
        "An error occurred when using {provider_name!r} to "
        "query the status of the instance: returned exit code {exit_code!r}: {stderr!s}."
    )

    def __init__(self, *, provider_name: str, exit_code: int, stderr: bytes) -> None:
        super().__init__(provider_name=provider_name, exit_code=exit_code, stderr=stderr.decode())


class ProviderInstanceNotFoundError(ProviderBaseError):

    fmt = "Cannot find an instance named {instance_name!r}."

    def __init__(self, *, instance_name: str) -> None:
        super().__init__(instance_name=instance_name)


class ProviderInfoDataKeyError(ProviderBaseError):

    fmt = (
        "The data returned by {provider_name!r} was not expected. "
        "It is missing a required key {missing_key!r} in {data!r}."
    )

    def __init__(self, *, provider_name: str, missing_key: str, data: Dict[str, Any]) -> None:
        super().__init__(provider_name=provider_name, missing_key=missing_key, data=data)


class ProviderBadDataError(ProviderBaseError):

    fmt = (
        "The data returned by {provider_name!r} was not expected "
        "or in the wrong format: {data!r}."
    )

    def __init__(self, *, provider_name: str, data: str) -> None:
        super().__init__(provider_name=provider_name, data=data)


class ProviderMultipassDownloadFailed(ProviderBaseError):
    fmt = (
        "Failed to download Multipass: {message!r}\n"
        "Please install manually. You can find the latest release at:\n"
        "https://multipass.run"
    )

    def __init__(self, message):
        super().__init__(message=message)


class ProviderMultipassInstallationFailed(ProviderBaseError):
    fmt = (
        "Failed to install Multipass: {message!r}\n"
        "Please install manually. You can find the latest release at:\n"
        "https://multipass.run"
    )

    def __init__(self, message):
        super().__init__(message=message)
