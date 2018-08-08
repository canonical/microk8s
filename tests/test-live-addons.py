from validators import (
    validate_dns,
    validate_dashboard,
    validate_storage,
    validate_ingress,
    validate_access
)
from utils import microk8s_enable, wait_for_pod_state, microk8s_disable


class TestLiveAddons(object):
    """
    Validates a microk8s with all the addons enabled
    """

    def test_dns(self):
        """
        Validates DNS works.

        """
        wait_for_pod_state("", "kube-system", "running", label="k8s-app=kube-dns")
        # Create a bbox
        validate_dns()

    def test_dashboard(self):
        """
        Validates dashboards works.

        """
        wait_for_pod_state("", "kube-system", "running", label="k8s-app=kube-dns")
        validate_dashboard()

    def test_storage(self):
        """
        Validates storage works.

        """
        validate_storage()

    def test_ingress(self):
        """
        Validates storage works.

        """
        validate_ingress()

    def test_access(self):
        """
        Validates api access.

        """
        validate_access()

