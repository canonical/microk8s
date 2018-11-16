import pytest
import platform

from validators import (
    validate_dns_dashboard,
    validate_storage,
    validate_ingress,
    validate_gpu,
    validate_istio,
    validate_registry,
    validate_forward,
    validate_metrics_server,
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

    def test_dns_dashboard(self):
        """
        Sets up dashboard and validates it works.

        """
        print("Enabling DNS")
        microk8s_enable("dns")
        wait_for_pod_state("", "kube-system", "running", label="k8s-app=kube-dns")
        print("Enabling dashboard")
        microk8s_enable("dashboard")
        print("Validating dashboard")
        validate_dns_dashboard()
        print("Disabling DNS")
        microk8s_disable("dns")
        print("Disabling dashboard")
        microk8s_disable("dashboard")

    def test_storage_registry(self):
        """
        Sets up and tests the storage addon and the private registry.

        """
        print("Enabling storage")
        microk8s_enable("storage")
        print("Validating storage")
        validate_storage()
        microk8s_enable("registry")
        print("Validating registry")
        validate_registry()
        print("Disabling registry")
        microk8s_disable("registry")
        print("Disabling storage")
        p = Popen("/snap/bin/microk8s.disable storage".split(), stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        p.communicate(input=b'Y\n')[0]

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
        if platform.machine() != 'x86_64':
            print("GPU tests are only relevant in x86 architectures")
            return

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

    def test_istio(self):
        """
        Sets up and validate istio.

        """
        if platform.machine() != 'x86_64':
            print("Istio tests are only relevant in x86 architectures")
            return

        print("Enabling Istio")
        p = Popen("/snap/bin/microk8s.enable istio".split(), stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        p.communicate(input=b'N\n')[0]
        print("Validating Istio")
        validate_istio()
        print("Disabling Istio")
        microk8s_disable("istio")
        print("Disabling DNS")
        microk8s_disable("dns")

    def test_forward(self):
        """
        Test port forward.

        """
        print("Validating Port Forward")
        validate_forward()

    def test_metrics_server(self):
        """
        Test the metrics server.

        """
        print("Enabling metrics-server")
        microk8s_enable("metrics-server")
        print("Validating the Metrics Server")
        validate_metrics_server()
        print("Disabling metrics-server")
        microk8s_disable("metrics-server")

