import pytest
import os
import platform

from validators import (
    validate_dns_dashboard,
    validate_storage,
    validate_ingress,
    validate_gpu,
    validate_istio,
    validate_knative,
    validate_registry,
    validate_forward,
    validate_metrics_server,
    validate_prometheus,
    validate_fluentd,
    validate_jaeger,
    validate_linkerd,
    validate_rbac,
    validate_kubeflow,
)
from utils import (
    microk8s_enable,
    wait_for_pod_state,
    wait_for_namespace_termination,
    microk8s_disable,
    microk8s_reset
)
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
        print("Enabling ingress")
        microk8s_enable("ingress")
        print("Validating ingress")
        validate_ingress()
        print("Disabling ingress")
        microk8s_disable("ingress")
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
        print("Validating Port Forward")
        validate_forward()
        print("Disabling registry")
        microk8s_disable("registry")
        print("Disabling dashboard")
        microk8s_disable("dashboard")
        print("Disabling storage")
        microk8s_disable("storage:destroy-storage")
        '''
        We would disable DNS here but this freezes any terminating pods.
        We let microk8s.reset to do the cleanup.
        print("Disabling DNS")
        microk8s_disable("dns")
        '''

    @pytest.mark.skipif(os.environ.get('UNDER_TIME_PRESSURE') == 'True', reason = "Skipping istio and knative tests as we are under time pressure")
    @pytest.mark.skipif(platform.machine() != 'x86_64', reason = "GPU tests are only relevant in x86 architectures")
    def test_gpu(self):
        """
        Sets up nvidia gpu in a gpu capable system. Skip otherwise.

        """
        try:
            print("Enabling gpu")
            gpu_enable_outcome = microk8s_enable("gpu")
        except CalledProcessError:
            # Failed to enable gpu. Skip the test.
            print("Could not enable GPU support")
            return
        validate_gpu()
        print("Disable gpu")
        microk8s_disable("gpu")

    @pytest.mark.skipif(platform.machine() != 'x86_64', reason = "Istio tests are only relevant in x86 architectures")
    @pytest.mark.skipif(os.environ.get('UNDER_TIME_PRESSURE') == 'True', reason = "Skipping istio and knative tests as we are under time pressure")    
    def test_knative_istio(self):
        """
        Sets up and validate istio.

        """

        print("Enabling Knative and Istio")
        p = Popen("/snap/bin/microk8s.enable knative".split(), stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        p.communicate(input=b'N\n')[0]
        print("Validating Istio")
        validate_istio()
        print("Validating Knative")
        validate_knative()
        print("Disabling Knative")
        microk8s_disable("knative")
        wait_for_namespace_termination("knative-serving", timeout_insec=600)
        print("Disabling Istio")
        microk8s_disable("istio")

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

    @pytest.mark.skipif(platform.machine() != 'x86_64', reason = "Fluentd, prometheus, jaeger tests are only relevant in x86 architectures")
    @pytest.mark.skipif(os.environ.get('UNDER_TIME_PRESSURE') == 'True', reason = "Skipping cilium tests as we are under time pressure")    
    def test_monitoring_addons(self):
        """
        Test jaeger, prometheus and fluentd.

        """

        # Prometheus operator on our lxc is chashlooping disabling the test for now.
        #print("Enabling prometheus")
        #microk8s_enable("prometheus")
        #print("Validating Prometheus")
        #validate_prometheus()
        #print("Disabling prometheus")
        #microk8s_disable("prometheus")
        print("Enabling fluentd")
        microk8s_enable("fluentd")
        print("Enabling jaeger")
        microk8s_enable("jaeger")
        print("Validating the Jaeger operator")
        validate_jaeger()
        print("Validating the Fluentd")
        validate_fluentd()
        print("Disabling jaeger")
        microk8s_disable("jaeger")
        print("Disabling fluentd")
        microk8s_disable("fluentd")

    @pytest.mark.skipif(platform.machine() != 'x86_64', reason = "Linkerd tests are only relevant in x86 architectures")
    @pytest.mark.skipif(os.environ.get('UNDER_TIME_PRESSURE') == 'True', reason = "Skipping Linkerd tests as we are under time pressure")    
    def test_linkerd(self):
        """
        Sets up and validate linkerd

        """
        print("Enabling Linkerd")
        microk8s_enable("linkerd")
        print("Validating Linkerd")
        validate_linkerd()
        print("Disabling Linkerd")
        microk8s_disable("linkerd")

    def test_rbac_addon(self):
        """
        Test RBAC.

        """
        print("Enabling RBAC")
        microk8s_enable("rbac")
        print("Validating RBAC")
        validate_rbac()
        print("Disabling RBAC")
        microk8s_disable("rbac")

    @pytest.mark.skip("disabling the kubelfow addon until the new bundle becomes available")
    @pytest.mark.skipif(platform.machine() != 'x86_64', reason = "Kubeflow tests are only relevant in x86 architectures")
    @pytest.mark.skipif(os.environ.get('UNDER_TIME_PRESSURE') == 'True', reason = "Skipping kubeflow test as we are under time pressure")
    def test_kubeflow_addon(self):
        """
        Test kubeflow.

        """

        print("Enabling Kubeflow")
        microk8s_enable("kubeflow")
        print("Validating Kubeflow")
        validate_kubeflow()
        print("Disabling kubeflow")
        microk8s_disable("kubeflow")
