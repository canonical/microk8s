import ctypes
import logging
import os
import subprocess

from abc import ABC
from os.path import realpath
from shutil import disk_usage

from .file_utils import get_kubeconfig_path, get_kubectl_directory

logger = logging.getLogger(__name__)


class Auxiliary(ABC):
    """
    Base OS auxiliary class.
    """

    def __init__(self, args) -> None:
        """
        :param args: ArgumentParser
        :return: None
        """
        self._args = args

        if getattr(self._args, "disk", None):
            self.minimum_disk = self._args.disk * 1024 * 1024 * 1024
        else:
            self.minimum_disk = 0

    @staticmethod
    def _free_space() -> int:
        """
        Get space free of disk that this script is installed to.

        :return: Integer free space
        """
        return disk_usage(realpath("/")).free

    def is_enough_space(self) -> bool:
        """
        Compare free space with minimum.

        :return: Boolean
        """
        return self._free_space() > self.minimum_disk

    def get_kubectl_directory(self) -> str:
        """
        Get the correct directory to install kubectl into,
        we can then call this when running `microk8s kubectl`
        without interfering with any systemwide install.

        :return: String
        """
        return get_kubectl_directory()

    def get_kubeconfig_path(self) -> str:
        """
        Get the correct path to write the kubeconfig
        file to.  This is then read by the installed
        kubectl and won't interfere with one in the user's
        home.

        :return: String
        """
        return get_kubeconfig_path()

    def kubectl(self) -> int:
        """
        Run kubectl on the host, with the generated kubeconf.

        :return: None
        """
        kctl_dir = self.get_kubectl_directory()
        try:
            exit_code = subprocess.check_call(
                [
                    os.path.join(kctl_dir, "kubectl"),
                    "--kubeconfig={}".format(self.get_kubeconfig_path()),
                ]
                + self._args,
            )
        except subprocess.CalledProcessError as e:
            return e.returncode
        else:
            return exit_code


class Windows(Auxiliary):
    """
    Windows auxiliary methods.
    """

    def __init__(self, args) -> None:
        """
        :param args: ArgumentParser
        :return: None
        """
        super(Windows, self).__init__(args)

    @staticmethod
    def check_admin() -> bool:
        """
        Check if running as admin.

        :return: Boolean
        """
        return ctypes.windll.shell32.IsUserAnAdmin() == 1

    @staticmethod
    def check_hyperv() -> bool:
        """
        Check if Hyper V is already enabled.

        :return: Boolean
        """
        try:
            out = subprocess.check_output(
                ["DISM", "/Online", "/Get-FeatureInfo", "/FeatureName:Microsoft-Hyper-V"]
            )
        except subprocess.CalledProcessError:
            return False

        if "State : Disabled" in out.decode():
            return False

        return True

    @staticmethod
    def enable_hyperv() -> None:
        """
        Enable Hyper V feature.

        :return: None
        """
        try:
            subprocess.check_call(
                [
                    "DISM",
                    "/Online",
                    "/Enable-Feature",
                    "/All",
                    "/NoRestart",
                    "/FeatureName:Microsoft-Hyper-V",
                ]
            )
        except subprocess.CalledProcessError as e:
            if e.returncode == 3010:
                pass  # This is fine, because Windows.
            else:
                raise


class Linux(Auxiliary):
    """
    MacOS auxiliary methods.
    """

    def __init__(self, args) -> None:
        """
        :param args: ArgumentParser
        :return: None
        """
        super(Linux, self).__init__(args)


class MacOS(Linux):
    """
    MacOS auxiliary methods.
    """

    def __init__(self, args) -> None:
        """
        :param args: ArgumentParser
        :return: None
        """
        super(MacOS, self).__init__(args)
