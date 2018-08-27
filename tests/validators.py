import time
import os
import re
import requests

from utils import (
    kubectl,
    wait_for_pod_state,
    kubectl_get,
    wait_for_installation,
    docker,
)

def validate_dns():
    """
    Validate DNS by starting a busy box and nslookuping the kubernetes default service.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "bbox.yaml")
    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state("busybox", "default", "running")
    output = kubectl("exec -ti busybox -- nslookup kubernetes.default.svc.cluster.local")
    assert "10.152.183.1" in output
    kubectl("delete -f {}".format(manifest))


def validate_dashboard():
    """
    Validate the dashboard addon by looking at the grafana URL.
    """
    wait_for_pod_state("", "kube-system", "running", label="k8s-app=influxGrafana")
    cluster_info = kubectl("cluster-info")
    # Cluster info output is colored so we better search for the port in the url pattern
    # instead of trying to extract the url substring
    regex = "http://127.0.0.1:([0-9]+)/api/v1/namespaces/kube-system/services/monitoring-grafana/proxy"
    grafana_pattern = re.compile(regex)
    for url in cluster_info.split():
        port_search = grafana_pattern.search(url)
        if port_search:
            break

    grafana_url = "http://127.0.0.1:{}" \
                  "/api/v1/namespaces/kube-system/services/" \
                  "monitoring-grafana/proxy".format(port_search.group(1))
    assert grafana_url

    attempt = 50
    while attempt >= 0:
        resp = requests.get(grafana_url)
        if resp.status_code == 200:
            break
        time.sleep(2)
        attempt -= 1
    assert resp.status_code == 200


def validate_storage():
    """
    Validate storage by creating a PVC.
    """
    wait_for_pod_state("", "kube-system", "running", label="k8s-app=hostpath-provisioner")
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "pvc.yaml")
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


def validate_ingress():
    """
    Validate ingress by creating a ingress rule.
    """
    wait_for_pod_state("", "default", "running", label="app=default-http-backend")
    wait_for_pod_state("", "default", "running", label="name=nginx-ingress-microk8s")
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "ingress.yaml")
    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state("", "default", "running", label="app=microbot")

    attempt = 50
    while attempt >= 0:
        output = kubectl("get ing")
        if "microbot.127.0.0.1.xip.io" in output:
            break
        time.sleep(2)
        attempt -= 1
    assert "microbot.127.0.0.1.xip.io" in output

    attempt = 50
    while attempt >= 0:
        resp = requests.get("http://microbot.127.0.0.1.xip.io")
        if resp.status_code == 200:
            break
        time.sleep(2)
        attempt -= 1
    assert resp.status_code == 200
    assert "microbot.png" in resp.content.decode("utf-8")

    kubectl("delete -f {}".format(manifest))


def validate_gpu():
    """
    Validate gpu by trying a cuda-add.
    """
    wait_for_pod_state("", "kube-system", "running", label="name=nvidia-device-plugin-ds")
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "cuda-add.yaml")

    get_pod = kubectl_get("po")
    if "cuda-vector-add" in str(get_pod):
        # Cleanup
        kubectl("delete -f {}".format(manifest))
        time.sleep(10)

    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state("cuda-vector-add", "default", "terminated")
    result = kubectl("logs pod/cuda-vector-add")
    assert "PASSED" in result


def validate_istio():
    """
    Validate istio by deploying the bookinfo app.
    """
    wait_for_installation()
    istio_services = [
        "citadel",
        "egressgateway",
        "galley",
        "ingressgateway",
        "sidecar-injector",
        "statsd-prom-bridge",
    ]
    for service in istio_services:
        wait_for_pod_state("", "istio-system", "running", label="istio={}".format(service))

    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "bookinfo.yaml")
    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state("", "default", "running", label="app=details")
    kubectl("delete -f {}".format(manifest))


def validate_registry():
    """
    Validate the private registry.
    """
    wait_for_pod_state("", "container-registry", "running", label="app=registry")
    docker("pull busybox")
    docker("tag busybox localhost:32000/my-busybox")
    docker("push localhost:32000/my-busybox")

    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "bbox-local.yaml")
    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state("busybox", "default", "running")
    output = kubectl("describe po busybox")
    assert "localhost:32000/my-busybox" in output
    kubectl("delete -f {}".format(manifest))


def validate_forward():
    """
    Validate ports are forwarded
    """
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "nginx-pod.yaml")
    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state("", "default", "running", label="app=nginx")
    os.system('killall kubectl')
    os.system('/snap/bin/microk8s.kubectl port-forward pod/nginx 5000:80 &')
    attempt = 10
    while attempt >= 0:
        try:
            resp = requests.get("http://localhost:5000")
            if resp.status_code == 200:
                break
        except:
            pass
        attempt -= 1
        time.sleep(2)

    assert resp.status_code == 200

