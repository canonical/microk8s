import time
import os
import re
import requests
import platform
import yaml
import subprocess
from pathlib import Path

from utils import (
    get_arch,
    kubectl,
    wait_for_pod_state,
    docker,
    update_yaml_with_arch,
)

TEMPLATES = Path(__file__).absolute().parent / "templates"


def validate_dns_dashboard():
    """
    Validate the dashboard addon by trying to access the kubernetes dashboard.
    The dashboard will return an HTML indicating that it is up and running.
    """
    wait_for_pod_state("", "kube-system", "running", label="k8s-app=kubernetes-dashboard")
    wait_for_pod_state("", "kube-system", "running", label="k8s-app=dashboard-metrics-scraper")
    attempt = 30
    while attempt > 0:
        try:
            output = kubectl(
                "get "
                "--raw "
                "/api/v1/namespaces/kube-system/services/https:kubernetes-dashboard:/proxy/"
            )
            if "Kubernetes Dashboard" in output:
                break
        except subprocess.CalledProcessError:
            pass
        time.sleep(10)
        attempt -= 1

    assert attempt > 0


def validate_storage():
    """
    Validate storage by creating a PVC.
    """
    output = kubectl("describe deployment hostpath-provisioner -n kube-system")
    if "hostpath-provisioner-{}:1.0.0".format(get_arch()) in output:
        # we are running with a hostpath-provisioner that is old and we need to patch it
        cmd = (
            "set image  deployment hostpath-provisioner"
            "-n kube-system"
            "hostpath-provisioner=cdkbot/hostpath-provisioner:1.1.0"
        )
        kubectl(cmd)

    wait_for_pod_state("", "kube-system", "running", label="k8s-app=hostpath-provisioner")
    manifest = TEMPLATES / "pvc.yaml"
    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state("hostpath-test-pod", "default", "running")

    attempt = 50
    while attempt >= 0:
        output = kubectl("get pvc")
        if "Bound" in output:
            break
        time.sleep(2)
        attempt -= 1

    # Make sure the test pod writes data sto the storage
    found = False
    for root, dirs, files in os.walk("/var/snap/microk8s/common/default-storage"):
        for file in files:
            if file == "dates":
                found = True
    assert found
    assert "myclaim" in output
    assert "Bound" in output
    kubectl("delete -f {}".format(manifest))


def common_ingress():
    """
    Perform the Ingress validations that are common for all
    the Ingress controllers.
    """
    attempt = 50
    while attempt >= 0:
        output = kubectl("get ing")
        if "microbot.127.0.0.1.nip.io" in output:
            break
        time.sleep(5)
        attempt -= 1
    assert "microbot.127.0.0.1.nip.io" in output

    service_ok = False
    attempt = 50
    while attempt >= 0:
        try:
            resp = requests.get("http://microbot.127.0.0.1.nip.io/")
            if resp.status_code == 200 and "microbot.png" in resp.content.decode("utf-8"):
                service_ok = True
                break
        except requests.RequestException:
            time.sleep(5)
            attempt -= 1

    assert service_ok


def validate_ingress():
    """
    Validate ingress by creating a ingress rule.
    """
    daemonset = kubectl("get ds")
    if "nginx-ingress-microk8s-controller" in daemonset:
        wait_for_pod_state("", "default", "running", label="app=default-http-backend")
        wait_for_pod_state("", "default", "running", label="name=nginx-ingress-microk8s")
    else:
        wait_for_pod_state("", "ingress", "running", label="name=nginx-ingress-microk8s")

    manifest = TEMPLATES / "ingress.yaml"
    update_yaml_with_arch(manifest)
    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state("", "default", "running", label="app=microbot")

    common_ingress()

    kubectl("delete -f {}".format(manifest))


def validate_registry():
    """
    Validate the private registry.
    """

    wait_for_pod_state("", "container-registry", "running", label="app=registry")
    pvc_stdout = kubectl("get pvc registry-claim -n container-registry -o yaml")
    pvc_yaml = yaml.safe_load(pvc_stdout)
    storage = pvc_yaml["spec"]["resources"]["requests"]["storage"]
    assert re.match("(^[2-9][0-9]{1,}|^[1-9][0-9]{2,})(Gi$)", storage)
    docker("pull busybox")
    docker("tag busybox localhost:32000/my-busybox")
    docker("push localhost:32000/my-busybox")

    manifest = TEMPLATES / "bbox-local.yaml"
    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state("busybox", "default", "running")
    output = kubectl("describe po busybox")
    assert "localhost:32000/my-busybox" in output
    kubectl("delete -f {}".format(manifest))


def validate_forward():
    """
    Validate ports are forwarded
    """
    manifest = TEMPLATES / "nginx-pod.yaml"
    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state("", "default", "running", label="app=nginx")
    os.system("killall kubectl")
    os.system("/snap/bin/microk8s.kubectl port-forward pod/nginx 5123:80 &")
    attempt = 10
    while attempt >= 0:
        try:
            resp = requests.get("http://localhost:5123")
            if resp.status_code == 200:
                break
        except requests.RequestException:
            pass
        attempt -= 1
        time.sleep(2)

    assert resp.status_code == 200
    os.system("killall kubectl")


def validate_metrics_server():
    """
    Validate the metrics server works
    """
    wait_for_pod_state("", "kube-system", "running", label="k8s-app=metrics-server")
    attempt = 30
    while attempt > 0:
        try:
            output = kubectl("get --raw /apis/metrics.k8s.io/v1beta1/pods")
            if "PodMetricsList" in output:
                break
        except subprocess.CalledProcessError:
            pass
        time.sleep(10)
        attempt -= 1

    assert attempt > 0


def validate_metallb_config(ip_ranges="192.168.0.105"):
    """
    Validate Metallb
    """
    if platform.machine() != "x86_64":
        print("Metallb tests are only relevant in x86 architectures")
        return
    out = kubectl(
        "get ipaddresspool -n metallb-system default-addresspool -o jsonpath='{.spec.addresses}"
    )
    for ip_range in ip_ranges.split(","):
        assert ip_range in out


def validate_dual_stack():
    # Deploy the test deployment and service
    manifest = TEMPLATES / "dual-stack.yaml"
    kubectl("apply -f {}".format(manifest))

    wait_for_pod_state("", "default", "running", label="run=nginxdualstack")

    ipv6_endpoint = kubectl(
        "get endpoints nginx6 "
        "-o jsonpath={.subsets[0].addresses[0].ip} "
        "--output=jsonpath=[{.subsets[0].addresses[0].ip}]"
    )

    print("Pinging endpoint: http://{}/".format(ipv6_endpoint))
    url = f"http://{ipv6_endpoint}/"
    attempt = 10
    service_ok = False
    while attempt >= 0:
        try:
            resp = requests.get(url)
            if "Kubernetes IPv6 nginx" in str(resp.content):
                print(resp.content)
                service_ok = True
                break
        except requests.RequestException:
            time.sleep(5)
            attempt -= 1

    assert service_ok
    kubectl("delete -f {}".format(manifest))
