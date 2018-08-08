import pytest
from validators import (
    validate_dns,
    validate_dashboard,
    validate_storage,
    validate_ingress,
    validate_gpu,
    validate_access
)
from utils import microk8s_enable, wait_for_pod_state, microk8s_disable, microk8s_reset
from subprocess import Popen, PIPE, STDOUT, CalledProcessError


class TestAddons(object):

    @pytest.fixture(autouse=True)
    def clean_up(self):
        """
        Clean up after a test
        """
        yield
        microk8s_reset()

    def test_dns(self):
        """
        Sets up DNS addon and validates it works.

        """
        print("Enabling DNS")
        microk8s_enable("dns")
        wait_for_pod_state("", "kube-system", "running", label="k8s-app=kube-dns")
        # Create a bbox
        print("Validating dns")
        validate_dns()
        print("Disabling DNS")
        microk8s_disable("dns")

    def test_dashboard(self):
        """
        Sets up dashboard and validates it works.

        """
        print("Enabling DNS")
        microk8s_enable("dns")
        wait_for_pod_state("", "kube-system", "running", label="k8s-app=kube-dns")
        print("Enabling dashboard")
        microk8s_enable("dashboard")
        print("Validating dashboard")
        validate_dashboard()
        print("Disabling DNS")
        microk8s_disable("dns")
        print("Disabling dashboard")
        microk8s_disable("dashboard")

    def test_storage(self):
        """
        Sets up storage addon and validates it works.

        """
        print("Enabling storage")
        microk8s_enable("storage")
        print("Validating storage")
        validate_storage()
        print("Disabling storage")
        p = Popen("/snap/bin/microk8s.disable storage".split(), stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        disable = p.communicate(input=b'Y')[0]

    def test_ingress(self):
        """
        Sets up ingress addon and validates it works.

        """
        print("Enabling ingress")
        microk8s_enable("ingress")
        print("Validating ingress")
        validate_ingress()
        print("Disabling ingress")
        microk8s_disable("ingress")

    def test_gpu(self):
        """
        Sets up nvidia gpu in a gpu capable system. Skip otherwise.

        """
        print("Enabling dns")
        microk8s_enable("dns")
        try:
            print("Enabling gpu")
            gpu_enable_outcome = microk8s_enable("gpu")
        except CalledProcessError:
            # Failed to enable gpu. Skip the test.
            print("Disabling DNS")
            microk8s_disable("dns")
            return
        validate_gpu()
        print("Disable gpu")
        microk8s_disable("gpu")
        print("Disabling DNS")
        microk8s_disable("dns")

    def test_access(self):
        """
        Tests the API server access restrictions.

        """
        validate_access()
