#!/usr/bin/python3
from subprocess import check_output


def dashboard_proxy():
    print("Checking if Dashboard is running.")
    command = ["/snap/microk8s/current/microk8s-enable.wrapper", "dashboard"]
    output = check_output(command)
    if b"Addon dashboard is already enabled." not in output:
        print("Waiting for Dashboard to come up.")
        command = [
            "microk8s.kubectl",
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

    command = [
        "/snap/microk8s/current/microk8s-kubectl.wrapper",
        "-n",
        "kube-system",
        "get",
        "secret",
    ]
    output = check_output(command)
    secret_name = None
    for line in output.split(b"\n"):
        if line.startswith(b"default-token"):
            secret_name = line.split()[0].decode()
            break

    if not secret_name:
        print("Cannot find the dashboard secret.")

    command = [
        "/snap/microk8s/current/microk8s-kubectl.wrapper",
        "-n",
        "kube-system",
        "describe",
        "secret",
        secret_name,
    ]
    output = check_output(command)
    token = None
    for line in output.split(b"\n"):
        if line.startswith(b"token:"):
            token = line.split()[1].decode()

    if not token:
        print("Cannot find token from secret.")

    print("Dashboard will be available at https://127.0.0.1:10443")
    print("Use the following token to login:")
    print(token)

    command = [
        "/snap/microk8s/current/microk8s-kubectl.wrapper",
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
