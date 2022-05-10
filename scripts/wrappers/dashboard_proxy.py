#!/usr/bin/python3

import base64
import os
from subprocess import check_output, run
import time

import click

MICROK8S_ENABLE = os.path.expandvars("$SNAP/microk8s-enable.wrapper")
KUBECTL = os.path.expandvars("$SNAP/microk8s-kubectl.wrapper")
SECRET_YAML = """
apiVersion: v1
kind: Secret
metadata:
  name: microk8s-dashboard-proxy-token
  namespace: kube-system
  annotations:
    kubernetes.io/service-account.name: "default"
type: kubernetes.io/service-account-token
"""


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
def dashboard_proxy():
    """
    Enable the dashboard add-on and configures port-forwarding
    to allow accessing the dashboard from the local machine.
    """
    print("Checking if Dashboard is running.")
    command = [MICROK8S_ENABLE, "dashboard"]
    output = check_output(command)
    if b"Addon dashboard is already enabled." not in output:
        print("Waiting for Dashboard to come up.")
        command = [
            KUBECTL,
            "-n",
            "kube-system",
            "wait",
            "--timeout=240s",
            "deployment",
            "kubernetes-dashboard",
            "--for",
            "condition=available",
        ]
        check_output(command)

    print("Create token for accessing the dashboard")
    run([KUBECTL, "apply", "-f", "-"], input=SECRET_YAML.encode("ascii"))

    for attempt in range(20):
        print("Waiting for secret token (attempt {})".format(attempt))
        command = [
            KUBECTL,
            "-n",
            "kube-system",
            "get",
            "secret",
            "microk8s-dashboard-proxy-token",
            "-o",
            "jsonpath={.data.token}",
        ]
        output = check_output(command)
        if output:
            token = base64.b64decode(output).decode()
            break

        time.sleep(5)

    print("Dashboard will be available at https://127.0.0.1:10443")
    print("Use the following token to login:")
    print(token)

    command = [
        KUBECTL,
        "port-forward",
        "-n",
        "kube-system",
        "service/kubernetes-dashboard",
        "10443:443",
        "--address",
        "0.0.0.0",
    ]

    try:
        check_output(command)
    except KeyboardInterrupt:
        exit(0)


if __name__ == "__main__":
    dashboard_proxy()
