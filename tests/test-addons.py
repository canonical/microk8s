import pytest
import os
import platform
import sh
import yaml

from validators import (
    validate_dns_dashboard,
    validate_storage,
    validate_ingress,
    validate_ambassador,
    validate_gpu,
    validate_istio,
    validate_knative,
    validate_registry,
    validate_forward,
    validate_metrics_server,
    validate_fluentd,
    validate_jaeger,
    validate_keda,
    validate_linkerd,
    validate_rbac,
    validate_cilium,
    validate_multus,
    validate_kubeflow,
    validate_metallb_config,
    validate_prometheus,
    validate_traefik,
    validate_coredns_config,
    validate_portainer,
)
from utils import (
    microk8s_enable,
    wait_for_pod_state,
    wait_for_namespace_termination,
    microk8s_disable,
    microk8s_reset,
)
from subprocess import PIPE, STDOUT, CalledProcessError, check_call, run


class TestAddons(object):
    @pytest.fixture(scope="session", autouse=True)
    def clean_up(self):
        """
        Clean up after a test
        """
        yield
        microk8s_reset()

    def test_invalid_addon(self):
        with pytest.raises(sh.ErrorReturnCode_1):
            sh.microk8s.enable.foo()

    def test_help_text(self):
        status = yaml.load(sh.microk8s.status(format="yaml").stdout)
        expected = {a["name"]: "disabled" for a in status["addons"]}
        expected["ha-cluster"] = "enabled"

        assert expected == {a["name"]: a["status"] for a in status["addons"]}

        for addon in status["addons"]:
            sh.microk8s.enable(addon["name"], "--", "--help")

        assert expected == {a["name"]: a["status"] for a in status["addons"]}

        for addon in status["addons"]:
            sh.microk8s.disable(addon["name"], "--", "--help")

        assert expected == {a["name"]: a["status"] for a in status["addons"]}

    def test_basic(self):
        """
        Sets up and tests dashboard, dns, storage, registry, ingress, metrics server.

        """
        ip_ranges = "8.8.8.8,1.1.1.1"
        print("Enabling DNS")
        microk8s_enable("{}:{}".format("dns", ip_ranges), timeout_insec=500)
        wait_for_pod_state("", "kube-system", "running", label="k8s-app=kube-dns")
        print("Validating DNS config")
        validate_coredns_config(ip_ranges)
        print("Enabling ingress")
        microk8s_enable("ingress")
        print("Enabling metrics-server")
        microk8s_enable("metrics-server")
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
        print("Validating the Metrics Server")
        validate_metrics_server()
        print("Disabling metrics-server")
        microk8s_disable("metrics-server")
        print("Disabling registry")
        microk8s_disable("registry")
        print("Disabling dashboard")
        microk8s_disable("dashboard")
        print("Disabling storage")
        microk8s_disable("storage:destroy-storage")
        """
        We would disable DNS here but this freezes any terminating pods.
        We let microk8s reset to do the cleanup.
        print("Disabling DNS")
        microk8s_disable("dns")
        """

    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping GPU tests as we are under time pressure",
    )
    @pytest.mark.skipif(
        platform.machine() != "x86_64", reason="GPU tests are only relevant in x86 architectures"
    )
    def test_gpu(self):
        """
        Sets up nvidia gpu in a gpu capable system. Skip otherwise.

        """
        try:
            print("Enabling gpu")
            microk8s_enable("gpu")
        except CalledProcessError:
            # Failed to enable gpu. Skip the test.
            print("Could not enable GPU support")
            return
        validate_gpu()
        print("Disable gpu")
        microk8s_disable("gpu")

    @pytest.mark.skipif(
        platform.machine() != "x86_64", reason="Istio tests are only relevant in x86 architectures"
    )
    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping istio and knative tests as we are under time pressure",
    )
    def test_knative_istio(self):
        """
        Sets up and validate istio.

        """

        print("Enabling Knative and Istio")
        microk8s_enable("knative")
        print("Validating Istio")
        validate_istio()
        print("Validating Knative")
        validate_knative()
        print("Disabling Knative")
        microk8s_disable("knative")
        wait_for_namespace_termination("knative-serving", timeout_insec=600)
        print("Disabling Istio")
        microk8s_disable("istio")

    @pytest.mark.skipif(
        platform.machine() != "x86_64",
        reason="Fluentd, prometheus, jaeger tests are only relevant in x86 architectures",
    )
    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping jaeger, prometheus and fluentd tests as we are under time pressure",
    )
    def test_monitoring_addons(self):
        """
        Test jaeger, prometheus and fluentd.

        """

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

    @pytest.mark.skipif(
        platform.machine() != "x86_64",
        reason="Prometheus is only relevant in x86 architectures",
    )
    @pytest.mark.skipif(
        os.environ.get("SKIP_PROMETHEUS") == "True",
        reason="Skipping prometheus if it crash loops on lxd",
    )
    def test_prometheus(self):
        """
        Test prometheus.
        """

        print("Enabling prometheus")
        microk8s_enable("prometheus")
        print("Validating Prometheus")
        validate_prometheus()
        print("Disabling prometheus")
        microk8s_disable("prometheus")
        microk8s_reset()

    @pytest.mark.skipif(
        platform.machine() != "x86_64", reason="Cilium tests are only relevant in x86 architectures"
    )
    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping cilium tests as we are under time pressure",
    )
    def test_cilium(self):
        """
        Sets up and validates Cilium.
        """
        print("Enabling Cilium")
        run(
            "/snap/bin/microk8s.enable cilium".split(),
            stdout=PIPE,
            input=b"N\n",
            stderr=STDOUT,
            check=True,
        )
        print("Validating Cilium")
        validate_cilium()
        print("Disabling Cilium")
        microk8s_disable("cilium")
        microk8s_reset()

    @pytest.mark.skip("disabling the test while we work on a 1.20 release")
    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping Linkerd tests as we are under time pressure",
    )
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
    @pytest.mark.skipif(
        platform.machine() != "x86_64",
        reason="Kubeflow tests are only relevant in x86 architectures",
    )
    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping kubeflow test as we are under time pressure",
    )
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

    @pytest.mark.skipif(
        platform.machine() != "x86_64",
        reason="Metallb tests are only relevant in x86 architectures",
    )
    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping metallb test as we are under time pressure",
    )
    def test_metallb_addon(self):
        addon = "metallb"
        ip_ranges = "192.168.0.105-192.168.0.105,192.168.0.110-192.168.0.111,192.168.1.240/28"
        print("Enabling metallb")
        microk8s_enable("{}:{}".format(addon, ip_ranges), timeout_insec=500)
        validate_metallb_config(ip_ranges)
        print("Disabling metallb")
        microk8s_disable("metallb")

    @pytest.mark.skip("disabling the test while we work on a 1.20 release")
    @pytest.mark.skipif(
        platform.machine() != "x86_64",
        reason="Ambassador tests are only relevant in x86 architectures",
    )
    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping ambassador tests as we are under time pressure",
    )
    def test_ambassador(self):
        """
        Test Ambassador.

        """
        print("Enabling Ambassador")
        microk8s_enable("ambassador")
        print("Validating ambassador")
        validate_ambassador()
        print("Disabling Ambassador")
        microk8s_disable("ambassador")

    @pytest.mark.skipif(
        platform.machine() != "x86_64", reason="Multus tests are only relevant in x86 architectures"
    )
    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping multus tests as we are under time pressure",
    )
    def test_multus(self):
        """
        Sets up and validates Multus.
        """
        print("Enabling Multus")
        microk8s_enable("multus")
        print("Validating Multus")
        validate_multus()
        print("Disabling Multus")
        microk8s_disable("multus")

    def test_portainer(self):
        """
        Sets up and validates Portainer.
        """
        print("Enabling Portainer")
        microk8s_enable("portainer")
        print("Validating Portainer")
        validate_portainer()
        print("Disabling Portainer")
        microk8s_disable("portainer")

    def test_traefik(self):
        """
        Sets up and validates traefik.
        """
        print("Enabling traefik")
        microk8s_enable("traefik")
        print("Validating traefik")
        validate_traefik()
        print("Disabling traefik")
        microk8s_disable("traefik")

    @pytest.mark.skipif(
        platform.machine() != "x86_64", reason="KEDA tests are only relevant in x86 architectures"
    )
    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping KEDA tests as we are under time pressure",
    )
    def test_keda(self):
        """
        Sets up and validates keda.
        """
        print("Enabling keda")
        microk8s_enable("keda")
        print("Validating keda")
        validate_keda()
        print("Disabling keda")
        microk8s_disable("keda")

    def test_backup_restore(self):
        """
        Test backup and restore commands.
        """
        print("Checking dbctl backup and restore")
        if os.path.exists("backupfile.tar.gz"):
            os.remove("backupfile.tar.gz")
        check_call("/snap/bin/microk8s.dbctl --debug backup -o backupfile".split())
        check_call("/snap/bin/microk8s.dbctl --debug restore backupfile.tar.gz".split())
