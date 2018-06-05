import time
import os
import requests

from utils import kubectl, wait_for_pod_state


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
    grafana_url = "http://127.0.0.1:8080/api/v1/namespaces/kube-system/services/monitoring-grafana/proxy"
    assert grafana_url in cluster_info
    attempt = 5
    while attempt >= 0:
        resp = requests.get(grafana_url)
        if resp.status_code == 200:
            break
        time.sleep(20)
        attempt -= 1
    assert resp.status_code == 200


def validate_storage():
    """
    Validate storage by creating a PVC.
    """
    wait_for_pod_state("", "kube-system", "running", label="app=nfs-provisioner")
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "pvc.yaml")
    kubectl("apply -f {}".format(manifest))

    attempt = 5
    while attempt >= 0:
        output = kubectl("get pvc")
        if "Bound" in output:
            break
        time.sleep(20)
        attempt -= 1

    assert "myclaim" in output
    assert "Bound" in output
