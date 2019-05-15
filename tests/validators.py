import time
import os
import re
import requests
import platform

from utils import (
    kubectl,
    wait_for_pod_state,
    kubectl_get,
    wait_for_installation,
    docker,
    update_yaml_with_arch,
)


def validate_dns_dashboard():
    """
    Validate the dashboard addon by looking at the grafana URL.
    Validate DNS by starting a busy box and nslookuping the kubernetes default service.
    """
    wait_for_pod_state("", "kube-system", "running", label="k8s-app=influxGrafana")
    cluster_info = kubectl("cluster-info")
    # Cluster info output is colored so we better search for the port in the url pattern
    # instead of trying to extract the url substring
    regex = "http(.?)://127.0.0.1:([0-9]+)/api/v1/namespaces/kube-system/services/monitoring-grafana/proxy"
    grafana_pattern = re.compile(regex)
    for url in cluster_info.split():
        port_search = grafana_pattern.search(url)
        if port_search:
            break

    grafana_url = "http{}://127.0.0.1:{}" \
                  "/api/v1/namespaces/kube-system/services/" \
                  "monitoring-grafana/proxy".format(port_search.group(1), port_search.group(2))
    assert grafana_url

    attempt = 50
    while attempt >= 0:
        resp = requests.get(grafana_url, verify=False)
        if (resp.status_code == 200 and grafana_url.startswith('http://')) or \
            (resp.status_code == 401 and grafana_url.startswith('https://')):
            break
        time.sleep(2)
        attempt -= 1
    assert resp.status_code in [200, 401]


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
    update_yaml_with_arch(manifest)
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
    if platform.machine() != 'x86_64':
        print("GPU tests are only relevant in x86 architectures")
        return

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
    if platform.machine() != 'x86_64':
        print("Istio tests are only relevant in x86 architectures")
        return

    wait_for_installation()
    istio_services = [
        "citadel",
        "egressgateway",
        "galley",
        "ingressgateway",
        "sidecar-injector",
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
        except:
            pass
        time.sleep(10)
        attempt -= 1

    assert attempt > 0

def validate_prometheus():
    """
    Validate the prometheus operator
    """
    if platform.machine() != 'x86_64':
        print("Prometheus tests are only relevant in x86 architectures")
        return

    wait_for_pod_state("prometheus-k8s-0", "monitoring", "running", timeout_insec=1200)
    wait_for_pod_state("alertmanager-main-0", "monitoring", "running", timeout_insec=1200)


def validate_fluentd():
    """
    Validate fluentd
    """
    if platform.machine() != 'x86_64':
        print("Fluentd tests are only relevant in x86 architectures")
        return

    wait_for_pod_state("elasticsearch-logging-0", "kube-system", "running")
    wait_for_pod_state("", "kube-system", "running", label="k8s-app=fluentd-es")
    wait_for_pod_state("", "kube-system", "running", label="k8s-app=kibana-logging")

def validate_jaeger():
    """
    Validate the jaeger operator
    """
    if platform.machine() != 'x86_64':
        print("Jaeger tests are only relevant in x86 architectures")
        return

    wait_for_pod_state("", "default", "running", label="name=jaeger-operator")
    attempt = 30
    while attempt > 0:
        try:
            output = kubectl("get ingress")
            if "simplest-query" in output:
                break
        except:
            pass
        time.sleep(2)
        attempt -= 1

    assert attempt > 0

def validate_linkerd():
    """
    Validate Linkerd by deploying emojivoto.
    """
    if platform.machine() != 'x86_64':
        print("Linkerd tests are only relevant in x86 architectures")
        return

    wait_for_installation()

    wait_for_pod_state("", "linkerd", "running", label="linkerd.io/control-plane-ns")

    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "emojivoto.yaml")
    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state("", "emojivoto", "running", label="app=emoji-svc")
    kubectl("delete -f {}".format(manifest))

def validate_rbac():
    """
    Validate RBAC is actually on
    """
    output = kubectl("auth can-i --as=system:serviceaccount:default:default view pod", err_out='no')
    assert "no" in output
    output = kubectl("auth can-i --as=admin --as-group=system:masters view pod")
    assert "yes" in output
