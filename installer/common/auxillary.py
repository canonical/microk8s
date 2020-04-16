import logging
import subprocess

logger = logging.getLogger(__name__)


class Auxillary(object):
    """
    Base OS auxillary class.
    """
    def __init__(self) -> None:
        pass


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
                '/All',
                '/Online',
                '/Enable-Feature',
                '/NoRestart',
                '/FeatureName:Microsoft-Hyper-V'
            ])
        except subprocess.CalledProcessError as e:
            if e.returncode == 3010:
                pass  # This is fine, because Windows.
            else:
                raise
