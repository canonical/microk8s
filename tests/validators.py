import time
import os
import re
import requests
import platform
import yaml
import subprocess

from utils import (
    kubectl,
    wait_for_pod_state,
    kubectl_get,
    wait_for_installation,
    docker,
    update_yaml_with_arch,
    run_until_success,
    get_pod_by_label,
)


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


def validate_dashboard_ingress():
    """
    Validate the ingress for dashboard addon by trying to access the kubernetes dashboard
    using ingress ports. The dashboard will return HTTP 200 and HTML indicating that it is
    up and running.
    """
    service_ok = False
    attempt = 50
    while attempt >= 0:
        try:
            resp = requests.get(
                "https://kubernetes-dashboard.127.0.0.1.nip.io/#/login", verify=False
            )
            if resp.status_code == 200 and "Kubernetes Dashboard" in resp.content.decode("utf-8"):
                service_ok = True
                break
        except requests.RequestException:
            time.sleep(5)
            attempt -= 1

    assert service_ok


def validate_storage():
    """
    Validate storage by creating a PVC.
    """
    namespace = "kube-system"
    for label in ["app.kubernetes.io/name=hostpath-provisioner", "k8s-app=hostpath-provisioner"]:
        if get_pod_by_label(label, namespace):
            wait_for_pod_state(
                "",
                namespace,
                "running",
                label=label,
            )
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

    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "ingress.yaml")
    update_yaml_with_arch(manifest)
    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state("", "default", "running", label="app=microbot")

    common_ingress()

    kubectl("delete -f {}".format(manifest))


def validate_ambassador():
    """
    Validate the Ambassador API Gateway by creating a ingress rule.
    """

    if platform.machine() != "x86_64":
        print("Ambassador tests are only relevant in x86 architectures")
        return

    wait_for_pod_state("", "ambassador", "running", label="product=aes")

    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "ingress.yaml")
    update_yaml_with_arch(manifest)
    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state("", "default", "running", label="app=microbot")

    # `Ingress`es must be annotatated for being recognized by Ambassador
    kubectl("annotate ingress microbot-ingress-nip kubernetes.io/ingress.class=ambassador")

    common_ingress()

    kubectl("delete -f {}".format(manifest))


def validate_gpu():
    """
    Validate gpu by trying a cuda-add.
    """
    if platform.machine() != "x86_64":
        print("GPU tests are only relevant in x86 architectures")
        return

    wait_for_pod_state(
        "", "gpu-operator-resources", "running", label="app=nvidia-device-plugin-daemonset"
    )
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


def validate_inaccel():
    """
    Validate inaccel by trying a vadd.
    """
    if platform.machine() != "x86_64":
        print("FPGA tests are only relevant in x86 architectures")
        return

    wait_for_pod_state("", "kube-system", "running", label="app.kubernetes.io/name=fpga-operator")
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "inaccel.yaml")

    get_pod = kubectl_get("po")
    if "inaccel-vadd" in str(get_pod):
        # Cleanup
        kubectl("delete -f {}".format(manifest))
        time.sleep(10)

    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state("inaccel-vadd", "default", "terminated")
    result = kubectl("logs pod/inaccel-vadd")
    assert "PASSED" in result


def validate_istio():
    """
    Validate istio by deploying the bookinfo app.
    """
    if platform.machine() != "x86_64":
        print("Istio tests are only relevant in x86 architectures")
        return

    wait_for_installation()
    istio_services = [
        "pilot",
        "egressgateway",
        "ingressgateway",
    ]
    for service in istio_services:
        wait_for_pod_state("", "istio-system", "running", label="istio={}".format(service))

    cmd = "/snap/bin/microk8s.istioctl verify-install"
    return run_until_success(cmd, timeout_insec=900, err_out="no")


def validate_knative():
    """
    Validate Knative by deploying the helloworld-go app.
    """
    if platform.machine() != "x86_64":
        print("Knative tests are only relevant in x86 architectures")
        return

    wait_for_installation()
    knative_services = [
        "activator",
        "autoscaler",
        "controller",
    ]
    for service in knative_services:
        wait_for_pod_state("", "knative-serving", "running", label="app={}".format(service))

    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "knative-helloworld.yaml")
    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state("", "default", "running", label="serving.knative.dev/service=helloworld-go")
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


def validate_prometheus():
    """
    Validate the prometheus operator
    """
    if platform.machine() != "x86_64":
        print("Prometheus tests are only relevant in x86 architectures")
        return

    wait_for_pod_state("prometheus-k8s-0", "monitoring", "running", timeout_insec=1200)
    wait_for_pod_state("alertmanager-main-0", "monitoring", "running", timeout_insec=1200)


def validate_fluentd():
    """
    Validate fluentd
    """
    if platform.machine() != "x86_64":
        print("Fluentd tests are only relevant in x86 architectures")
        return

    wait_for_pod_state("elasticsearch-logging-0", "kube-system", "running")
    wait_for_pod_state("", "kube-system", "running", label="k8s-app=fluentd-es")
    wait_for_pod_state("", "kube-system", "running", label="k8s-app=kibana-logging")


def validate_jaeger():
    """
    Validate the jaeger operator
    """
    if platform.machine() != "x86_64":
        print("Jaeger tests are only relevant in x86 architectures")
        return

    wait_for_pod_state("", "default", "running", label="name=jaeger-operator")
    attempt = 30
    while attempt > 0:
        try:
            output = kubectl("get ingress")
            if "simplest-query" in output:
                break
        except subprocess.CalledProcessError:
            pass
        time.sleep(2)
        attempt -= 1

    assert attempt > 0


def validate_linkerd():
    """
    Validate Linkerd by deploying emojivoto.
    """
    if platform.machine() != "x86_64":
        print("Linkerd tests are only relevant in x86 architectures")
        return

    wait_for_installation()
    wait_for_pod_state(
        "",
        "linkerd",
        "running",
        label="linkerd.io/control-plane-component=controller",
        timeout_insec=300,
    )
    print("Linkerd controller up and running.")
    wait_for_pod_state(
        "",
        "linkerd",
        "running",
        label="linkerd.io/control-plane-component=proxy-injector",
        timeout_insec=300,
    )
    print("Linkerd proxy injector up and running.")
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "emojivoto.yaml")
    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state("", "emojivoto", "running", label="app=emoji-svc", timeout_insec=600)
    kubectl("delete -f {}".format(manifest))


def validate_rbac():
    """
    Validate RBAC is actually on
    """
    output = kubectl("auth can-i --as=system:serviceaccount:default:default view pod", err_out="no")
    assert "no" in output
    output = kubectl("auth can-i --as=admin --as-group=system:masters view pod")
    assert "yes" in output


def cilium(cmd, timeout_insec=300, err_out=None):
    """
    Do a cilium <cmd>
    Args:
        cmd: left part of cilium <left_part> command
        timeout_insec: timeout for this job
        err_out: If command fails and this is the output, return.

    Returns: the cilium response in a string
    """
    cmd = "/snap/bin/microk8s.cilium " + cmd
    return run_until_success(cmd, timeout_insec, err_out)


def validate_cilium():
    """
    Validate cilium by deploying the bookinfo app.
    """
    if platform.machine() != "x86_64":
        print("Cilium tests are only relevant in x86 architectures")
        return

    wait_for_installation()
    wait_for_pod_state("", "kube-system", "running", label="k8s-app=cilium")

    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "nginx-pod.yaml")

    # Try up to three times to get nginx under cilium
    for attempt in range(0, 10):
        kubectl("apply -f {}".format(manifest))
        wait_for_pod_state("", "default", "running", label="app=nginx")
        output = cilium("endpoint list -o json", timeout_insec=20)
        if "nginx" in output:
            kubectl("delete -f {}".format(manifest))
            break
        else:
            print("Cilium not ready will retry testing.")
            kubectl("delete -f {}".format(manifest))
            time.sleep(20)
    else:
        print("Cilium testing failed.")
        assert False


def validate_multus():
    """
    Validate multus by making sure the multus pod is running.
    """

    wait_for_installation()
    wait_for_pod_state("", "kube-system", "running", label="app=multus")


def validate_kubeflow():
    """
    Validate kubeflow
    """
    if platform.machine() != "x86_64":
        print("Kubeflow tests are only relevant in x86 architectures")
        return

    wait_for_pod_state("ambassador-operator-0", "kubeflow", "running")


def validate_metallb_config(ip_ranges="192.168.0.105"):
    """
    Validate Metallb
    """
    if platform.machine() != "x86_64":
        print("Metallb tests are only relevant in x86 architectures")
        return
    out = kubectl("get configmap config -n metallb-system -o jsonpath='{.data.config}'")
    for ip_range in ip_ranges.split(","):
        assert ip_range in out


def validate_coredns_config(ip_ranges="8.8.8.8,1.1.1.1"):
    """
    Validate dns
    """
    out = kubectl("get configmap coredns -n kube-system -o jsonpath='{.data.Corefile}'")
    expected_forward_val = "forward ."
    for ip_range in ip_ranges.split(","):
        expected_forward_val = expected_forward_val + " " + ip_range
    assert expected_forward_val in out


def validate_keda():
    """
    Validate keda
    """
    wait_for_installation()
    wait_for_pod_state("", "keda", "running", label="app=keda-operator")
    print("KEDA operator up and running.")
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "keda-scaledobject.yaml")
    kubectl("apply -f {}".format(manifest))
    scaledObject = kubectl("-n gonuts get scaledobject.keda.sh")
    assert "stan-scaledobject" in scaledObject
    kubectl("delete -f {}".format(manifest))


def validate_traefik():
    """
    Validate traefik
    """
    wait_for_pod_state("", "traefik", "running", label="name=traefik-ingress-lb")


def validate_portainer():
    """
    Validate portainer
    """
    wait_for_pod_state("", "portainer", "running", label="app.kubernetes.io/name=portainer")


def validate_openfaas():
    """
    Validate openfaas
    """
    wait_for_pod_state("", "openfaas", "running", label="app=gateway")


def validate_openebs():
    """
    Validate OpenEBS
    """
    wait_for_installation()
    wait_for_pod_state(
        "",
        "openebs",
        "running",
        label="openebs.io/component-name=ndm",
        timeout_insec=900,
    )
    print("OpenEBS is up and running.")
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "openebs-test.yaml")
    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state(
        "", "default", "running", label="app=openebs-test-busybox", timeout_insec=900
    )
    output = kubectl("exec openebs-test-busybox -- ls /", timeout_insec=900, err_out="no")
    assert "my-data" in output
    kubectl("delete -f {}".format(manifest))


def validate_kata():
    """
    Validate Kata
    """
    wait_for_installation()
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "templates", "nginx-kata.yaml")
    kubectl("apply -f {}".format(manifest))
    wait_for_pod_state("", "default", "running", label="app=kata")
    kubectl("delete -f {}".format(manifest))
