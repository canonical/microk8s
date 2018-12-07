from validators import (
    validate_dns_dashboard,
    validate_storage,
    validate_ingress,
    validate_istio,
    validate_registry,
    validate_forward,
    validate_metrics_server,
    validate_prometheus,
    validate_fluentd,
    validate_jaeger,
)
from utils import wait_for_pod_state


class TestLiveAddons(object):
    """
    Validates a microk8s with all the addons enabled
    """

    def test_dns_dashboard(self):
        """
        Validates dns and dashboards work.

        """
        wait_for_pod_state("", "kube-system", "running", label="k8s-app=kube-dns")
        validate_dns_dashboard()

    def test_storage(self):
        """
        Validates storage works.

        """
        validate_storage()

    def test_ingress(self):
        """
        Validates ingress works.

        """
        validate_ingress()

    def test_istio(self):
        """
        Validate Istio works.

        """
        validate_istio()

    def test_registry(self):
        """
        Validates the registry works.

        """
        validate_registry()

    def test_forward(self):
        """
        Validates port forward works.

        """
        validate_forward()

    def test_metrics_server(self):
        """
        Validates metrics server works.

        """
        validate_metrics_server()

    def test_jaeger(self):
        """
        Validates jaeger operator.

        """
        validate_jaeger()
