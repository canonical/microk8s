#!/bin/env python3

from pathlib import Path
import datetime
import time

from jinja2 import Template
import requests


class Addon:
    """
    Base class for testing Microk8s addons.
    Validation requires a Kubernetes instance on the node
    """

    name = None

    def __init__(self, node):
        self.node = node

    def enable(self):
        return self.node.microk8s.enable([self.name])

    def disable(self):
        return self.node.microk8s.disable([self.name])

    def apply_template(self, template, context={}, yml=False):
        # Create manifest
        cwd = Path(__file__).parent
        template = cwd / "templates" / template
        with template.open() as f:
            rendered = Template(f.read()).render(context)
        render_path = f"/tmp/{template.stem}.yaml"
        self.node.write(render_path, rendered)

        return self.node.microk8s.kubectl.apply(["-f", render_path], yml=yml)

    def delete_template(self, template, context={}, yml=False):
        path = Path(template)
        render_path = f"/tmp/{path.stem}.yaml"

        return self.node.microk8s.kubectl.delete(["-f", render_path], yml=yml)


class Dns(Addon):
    """Microk8s dns addon"""

    name = "dns"

    def validate(self):
        self.node.kubernetes.wait_containers_ready(
            "kube-system", label="k8s-app=kube-dns", timeout=120
        )


class Dashboard(Addon):
    """Dashboard addon"""

    name = "dashboard"

    def validate(self):
        self.node.kubernetes.wait_containers_ready(
            "kube-system",
            label="k8s-app=kubernetes-dashboard",
            timeout=90,
        )
        self.node.kubernetes.wait_containers_ready(
            "kube-system", label="k8s-app=dashboard-metrics-scraper"
        )
        name = "https:kubernetes-dashboard:"
        result = self.node.kubernetes.get_service_proxy(name=name, namespace="kube-system")
        assert "Kubernetes Dashboard" in result


class Storage(Addon):
    """Storage addon"""

    name = "storage"

    def validate(self):
        self.node.kubernetes.wait_containers_ready(
            "kube-system", label="k8s-app=hostpath-provisioner"
        )
        claim = self.node.kubernetes.create_pvc(
            "testpvc", "kube-system", storage_class="microk8s-hostpath", wait=True
        )
        assert claim.spec.storage_class_name == "microk8s-hostpath"
        self.node.kubernetes.delete_pvc("testpvc", "kube-system")


class Ingress(Addon):
    """Ingress addon"""

    name = "ingress"

    def validate(self):
        # TODO: Is this still needed?
        # self.node.kubernetes.wait_containers_ready("default", label="app=default-http-backend")
        # self.node.kubernetes.wait_containers_ready("default", label="name=nginx-ingress-microk8s")
        self.node.kubernetes.wait_containers_ready("ingress", label="name=nginx-ingress-microk8s")

        # Create manifest
        context = {
            "arch": "amd64",
            "address": self.node.get_primary_address(),
        }
        self.apply_template("ingress.j2", context)

        self.node.kubernetes.wait_containers_ready("default", label="app=microbot")
        nip_addresses = self.node.kubernetes.wait_ingress_ready("microbot-ingress-nip", "default")
        xip_addresses = self.node.kubernetes.wait_ingress_ready("microbot-ingress-xip", "default")
        assert "127.0.0.1" in nip_addresses[0].ip
        assert "127.0.0.1" in xip_addresses[0].ip

        deadline = datetime.datetime.now() + datetime.timedelta(seconds=30)

        while True:
            resp = requests.get(f"http://microbot.{context['address']}.nip.io/")

            if resp.status_code == 200 or datetime.datetime.now() > deadline:
                break
            time.sleep(1)
        assert resp.status_code == 200
        assert "microbot.png" in resp.content.decode("utf8")

        deadline = datetime.datetime.now() + datetime.timedelta(seconds=30)

        while True:
            resp = requests.get(f"http://microbot.{context['address']}.xip.io/")

            if resp.status_code == 200 or datetime.datetime.now() > deadline:
                break
            time.sleep(1)
        assert resp.status_code == 200
        assert "microbot.png" in resp.content.decode("utf8")

        self.delete_template("ingress.j2", context)


class Gpu(Addon):
    """Gpu addon"""

    name = "gpu"

    def validate(self):
        self.node.kubernetes.wait_containers_ready(
            "kube-system", label="name=nvidia-device-plugin-ds"
        )

        # Create manifest
        context = {}
        self.apply_template("cuda-add.j2", context)
        # TODO: Finish validator on hardware with GPU
        self.delete_template("cuda-add.j2", context)


class Registry(Addon):
    """Registry addon"""

    name = "registry"

    def validate(self):
        self.node.kubernetes.wait_containers_ready(
            "container-registry", label="app=registry", timeout=300
        )
        claim = self.node.kubernetes.wait_pvc_phase("registry-claim", "container-registry")
        assert "20Gi" in claim.status.capacity["storage"]

        self.node.docker.cmd(["pull", "busybox"])
        self.node.docker.cmd(["tag", "busybox", "localhost:32000/my-busybox"])
        self.node.docker.cmd(["push", "localhost:32000/my-busybox"])

        context = {"image": "localhost:32000/my-busybox"}
        self.apply_template("bbox.j2", context)

        self.node.kubernetes.wait_containers_ready("default", field="metadata.name=busybox")
        pods = self.node.kubernetes.get_pods("default", field="metadata.name=busybox")
        assert pods[0].spec.containers[0].image == "localhost:32000/my-busybox"

        self.delete_template("bbox.j2", context)


class MetricsServer(Addon):

    name = "metrics-server"

    def validate(self):
        self.node.kubernetes.wait_containers_ready("kube-system", label="k8s-app=metrics-server")
        metrics_uri = "/apis/metrics.k8s.io/v1beta1/pods"
        reply = self.node.kubernetes.get_raw_api(metrics_uri)
        assert reply["kind"] == "PodMetricsList"


class Fluentd(Addon):

    name = "fluentd"

    def validate(self):
        self.node.kubernetes.wait_containers_ready(
            "kube-system", field="metadata.name=elasticsearch-logging-0", timeout=300
        )
        self.node.kubernetes.wait_containers_ready(
            "kube-system", label="k8s-app=fluentd-es", timeout=300
        )
        self.node.kubernetes.wait_containers_ready(
            "kube-system", label="k8s-app=kibana-logging", timeout=300
        )


class Jaeger(Addon):

    name = "jaeger"

    def validate(self):
        self.node.kubernetes.wait_containers_ready("default", label="name=jaeger-operator")
        self.node.kubernetes.wait_ingress_ready("simplest-query", "default", timeout=180)


class Metallb(Addon):

    name = "metallb"

    def enable(self, ip_ranges=None):
        if not ip_ranges:
            return self.node.microk8s.enable([self.name])
        else:
            return self.node.microk8s.enable([f"{self.name}:{ip_ranges}"])

    def validate(self, ip_ranges=None):
        context = {}
        self.apply_template("load-balancer.j2", context)
        ip = self.node.kubernetes.wait_load_balancer_ip("default", "example-service")

        if ip_ranges:
            assert ip in ip_ranges
        self.delete_template("load-balancer.j2", context)
