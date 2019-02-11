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
    validate_prometheus,
    validate_fluentd,
    validate_jaeger,
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

    def test_basic(self):
        """
        Sets up and tests dashboard, dns, storage, registry, ingress.

        """
        print("Enabling DNS")
        microk8s_enable("dns")
        wait_for_pod_state("", "kube-system", "running", label="k8s-app=kube-dns")
        print("Enabling dashboard")
        microk8s_enable("dashboard")
        print("Validating dashboard")
        validate_dns_dashboard()
        print("Enabling storage")
        microk8s_enable("storage")
        print("Validating storage")
        validate_storage()
        microk8s_enable("registry")
        print("Validating registry")
        validate_registry()
        print("Enabling ingress")
        microk8s_enable("ingress")
        print("Validating ingress")
        validate_ingress()
        print("Disabling ingress")
        microk8s_disable("ingress")
        print("Validating Port Forward")
        validate_forward()
        print("Disabling registry")
        microk8s_disable("registry")
        print("Disabling storage")
        p = Popen("/snap/bin/microk8s.disable storage".split(), stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        p.communicate(input=b'Y\n')[0]
        print("Disabling dashboard")
        microk8s_disable("dashboard")
        print("Disabling DNS")
        microk8s_disable("dns")

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

    def test_monitoring_addons(self):
        """
        Test jaeger, prometheus and fluentd.

        """
        if platform.machine() != 'x86_64':
            print("Fluentd, prometheus, jaeger tests are only relevant in x86 architectures")
            return

        print("Enabling fluentd")
        microk8s_enable("fluentd")
        print("Enabling prometheus")
        microk8s_enable("prometheus")
        print("Enabling jaeger")
        microk8s_enable("jaeger")
        print("Validating the Jaeger operator")
        validate_jaeger()
        print("Validating Prometheus")
        validate_prometheus()
        print("Validating the Fluentd")
        validate_fluentd()
        print("Disabling jaeger")
        microk8s_disable("jaeger")
        print("Disabling fluentd")
        microk8s_disable("fluentd")
        print("Disabling prometheus")
        microk8s_disable("prometheus")

