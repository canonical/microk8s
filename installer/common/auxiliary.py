import ctypes
import logging
import os
import psutil
import subprocess

from abc import ABC
from os.path import realpath
from shutil import disk_usage

from .file_utils import get_kubeconfig_path, get_kubectl_directory
from . import definitions

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
        try:
            self.requested_disk = self._args.disk * 1024 * 1024 * 1024
            self.requested_memory = self._args.mem * 1024 * 1024 * 1024
            self.requested_cores = self._args.cpu
        except AttributeError:
            self.requested_disk = definitions.DEFAULT_DISK_GB
            self.requested_memory = definitions.DEFAULT_MEMORY_GB
            self.requested_cores = definitions.DEFAULT_CORES

    @staticmethod
    def _free_disk_space() -> int:
        """
        Get space free of disk that this script is installed to.

        :return: Integer free space
        """
        return disk_usage(realpath("/")).free

    @staticmethod
    def _total_memory() -> int:
        """
        Get available memory in machine this script is installed to.

        :return: Available memory in bytes
        """
        return psutil.virtual_memory().total

    @staticmethod
    def _cpu_count() -> int:
        """
        Get the number of cpus on the machine this script is installed to.

        :return: Number of cpus
        """
        return psutil.cpu_count(logical=False)

    def has_enough_disk_space(self) -> bool:
        """
        Compare free space with minimum.

        :return: Boolean
        """
        return self._free_disk_space() > self.requested_disk

    def has_enough_memory(self) -> bool:
        """
        Compare requested memory against available

        :return: Boolean
        """
        return self._total_memory() > self.requested_memory

    def has_enough_cpus(self) -> bool:
        """
        Compare requested cpus against available cores.

        :return: Boolean
        """
        return self._cpu_count() >= self.requested_cores

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
