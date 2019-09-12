import pytest

from validators import (
    validate_dns_dashboard,
    validate_cluster,
)
from utils import (
    microk8s_enable,
    wait_for_pod_state,
    microk8s_disable,
    microk8s_reset,
    microk8s_clustering_capable
)


class TestCluster(object):

    @pytest.fixture(autouse=True)
    def clean_up(self):
        """
        Clean up after a test
        """
        yield
        microk8s_reset(2)

    def test_basic(self):
        """
        Sets up and tests dashboard, dns in a two node cluster.

        """
        if not microk8s_clustering_capable():
            return

        validate_cluster()
        print("Enabling DNS")
        microk8s_enable("dns")
        wait_for_pod_state("", "kube-system", "running", label="k8s-app=kube-dns")
        print("Enabling dashboard")
        microk8s_enable("dashboard")
        print("Validating dashboard")
        validate_dns_dashboard()
        print("Disabling dashboard")
        microk8s_disable("dashboard")
        '''
        We would disable DNS here but this freezes any terminating pods.
        We let microk8s.reset to do the cleanup.
        print("Disabling DNS")
        microk8s_disable("dns")
        '''
