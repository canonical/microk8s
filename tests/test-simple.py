import subprocess
import time
import requests
import os.path

import utils


class TestSimple(object):
    def test_microk8s_nodes_ready(self):
        # Get MicroK8s node status
        output = subprocess.check_output(["microk8s", "kubectl", "get", "nodes"])

        # Split the output into lines and skip the header
        lines = output.decode("utf-8").split("\n")[1:]

        # Iterate through the lines to check the node status
        for line in lines:
            # Split the line by whitespace
            parts = line.split()
            # Check if the node status is "Ready"
            if len(parts) > 1 and parts[1] != "Ready":
                # If any node is not in "Ready" status, fail the test
                assert False, f"Node {parts[0]} is not in Ready status"

    def test_calico_cni_pods_running(self):
        # Get Calico CNI pod status
        output = subprocess.check_output(
            ["microk8s", "kubectl", "get", "pods", "-n", "kube-system"]
        )

        # Split the output into lines and skip the header
        lines = output.decode("utf-8").split("\n")[1:]

        # Iterate through the lines to check the Calico CNI pod status
        for line in lines:
            # Split the line by whitespace
            parts = line.split()
            # Check if the pod is related to Calico CNI and not in the "Running" state
            if len(parts) >= 4 and parts[0].startswith("calico") and parts[2] != "Running":
                # If any Calico CNI pod is not in the "Running" state, fail the test
                assert False, f"Calico CNI pod {parts[0]} is not running"

    def test_nginx_ingress(self):
        # Create Ingress resource for the Nginx pod
        subprocess.run(
            ["microk8s", "kubectl", "apply", "-f", "tests/templates/simple-deploy.yaml"], check=True
        )

        # Wait for the pod to be in a ready state
        subprocess.run(
            [
                "microk8s",
                "kubectl",
                "rollout",
                "status",
                "deployment",
                "nginx-deployment",
                "-n",
                "default",
                "--timeout=90s",
            ],
            check=True,
        )

        # Send a curl request to the Ingress IP
        if "core/ingress: enabled" not in subprocess.check_output(
            ["microk8s", "status", "--format", "short"]
        ).decode("utf-8"):
            output = subprocess.check_output(
                [
                    "microk8s",
                    "kubectl",
                    "get",
                    "svc",
                    "nginx-service",
                    "-o",
                    "jsonpath={.spec.clusterIP}",
                ]
            )
            response = requests.get(f"http://{output.decode('utf-8')}:80", timeout=15)
        else:
            # Wait for ingress to be ready
            time.sleep(3)
            response = requests.get("http://127.0.0.1:80", timeout=15)

        subprocess.run(
            ["microk8s", "kubectl", "delete", "-f", "tests/templates/simple-deploy.yaml"],
            check=True,
        )

        # Verify the HTTP status code is 200
        assert response.status_code == 200

    def test_microk8s_services_running(self):
        # Define the services to check for control plane and worker nodes
        node_services = [
            "snap.microk8s.daemon-kubelite.service",
            "snap.microk8s.daemon-containerd.service",
            "snap.microk8s.daemon-cluster-agent.service",
        ]
        control_plane_services = [
            "snap.microk8s.daemon-apiserver-kicker.service",
            "snap.microk8s.daemon-k8s-dqlite.service",
        ]
        worker_node_services = ["snap.microk8s.daemon-apiserver-proxy.service"]

        if os.path.exists("/var/snap/microk8s/current/var/lock/clustered.lock"):
            node_services += worker_node_services
        else:
            node_services += control_plane_services

        # Get the list of running systemd services
        output = subprocess.check_output(["systemctl", "list-units", "--state=running"])

        # Split the output into lines and skip the header
        lines = output.decode("utf-8").split("\n")[1:]

        # Create sets to store the running services for control plane and worker nodes
        running_node_services = set()

        # Iterate through the lines to check the running services
        for line in lines:
            # Split the line by whitespace
            parts = line.split()

            # Check if the line contains a running service
            if len(parts) >= 2 and parts[0].endswith(".service"):
                service_name = parts[0]

                # Check if the running service is in the control plane services list
                if service_name in node_services:
                    running_node_services.add(service_name)

        # Verify that all node services are running
        assert running_node_services == set(node_services), "Not all node services are running"

    def test_microk8s_stop_start(self):
        coredns_procs = utils._get_process("coredns")
        assert len(coredns_procs) > 0, "Expected to find a coredns process running."

        utils.run_until_success("/snap/bin/microk8s.stop", timeout_insec=180)

        new_coredns_procs = utils._get_process("coredns")
        assert len(new_coredns_procs) == 0, "coredns found still running after microk8s stop."

        utils.run_until_success("/snap/bin/microk8s.start", timeout_insec=180)

        new_coredns_procs = utils._get_process("coredns")
        assert len(new_coredns_procs) > 0, "Expected to find a new coredns process running."
