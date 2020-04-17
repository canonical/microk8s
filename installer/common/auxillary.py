import logging
import subprocess

from . import definitions
from os.path import realpath
from shutil import disk_usage

logger = logging.getLogger(__name__)


class Auxillary(object):
    """
    Base OS auxillary class.
    """
    def __init__(self) -> None:
        """
        :return: None
        """
        self.minimum_disk = \
            definitions.DEFAULT_DISK * 1024 * 1024 * 1024

    @staticmethod
    def _free_space() -> int:
        """
        Get space free of disk that this script is installed to.

        :return: Integer free space
        """
        return disk_usage(realpath('/')).free

    def is_enough_space(self) -> bool:
        """
        Compare free space with minimum.

        :return: Boolean
        """
        return self._free_space() > self.minimum_disk


class Windows(Auxillary):
    """
    Windows auxillary methods.
    """
    def __init__(self) -> None:
        """
        :return: None
        """
        super(Windows, self).__init__()

    def check_hyperv(self) -> bool:
        """
        Check if Hyper V is already enabled.
        """
        try:
            out = subprocess.check_output([
                'DISM',
                '/Online',
                '/Get-FeatureInfo',
                '/FeatureName:Microsoft-Hyper-V'
            ])
        except subprocess.CalledProcessError:
            return False

        if 'State : Disabled' in out.decode():
            return False

        return True

    def enable_hyperv(self) -> None:
        """
        Enable Hyper V feature.
        """
        try:
            subprocess.check_call([
                'DISM',
                '/Online',
                '/Enable-Feature',
                '/All',
                '/NoRestart',
                '/FeatureName:Microsoft-Hyper-V'
            ])
        except subprocess.CalledProcessError as e:
            if e.returncode == 3010:
                pass  # This is fine, because Windows.
            else:
                raise
