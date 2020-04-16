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
            subprocess.check_call([
                'DISM',
                '/Online',
                '/Get-FeatureInfo',
                '/FeatureName:Microsoft-Hyper-V'
            ])
        except subprocess.CalledProcessError:
            return False
        else:
            return True

    def enable_hyperv(self) -> None:
        """
        Enable Hyper V feature.
        """
        subprocess.call([
            'DISM',
            '/Online',
            '/Enable-Feature',
            '/All',
            '/NoRestart',
            '/FeatureName:Microsoft-Hyper-V'
        ])

