#!/usr/bin/env python3

import json
import subprocess
import os

import click

CTR = os.path.expandvars("$SNAP/microk8s-ctr.wrapper")
KUBECTL = [
    "{}/kubectl".format(os.getenv("SNAP")),
    "--kubeconfig={}/credentials/kubelet.config".format(os.getenv("SNAP_DATA")),
]


@click.command("kill-host-pods")
@click.argument("selector", nargs=-1)
@click.option("--dry-run", is_flag=True, default=False)
def main(selector: list, dry_run: bool):
    """
    Delete pods running on the local node based on Kubernetes selectors.

    Example usage:

    $ ./kill-host-pods.py -- -n kube-system -l k8s-app=calico-node
    """
    containers = subprocess.check_output([CTR, "container", "ls", "-q"]).decode().split("\n")
    out = subprocess.check_output([*KUBECTL, "get", "pod", "-o", "json", *selector])

    pods = json.loads(out)
    for pod in pods["items"]:
        must_delete = False
        for container in pod["status"]["containerStatuses"] or []:
            try:
                _, container_id = container["containerID"].split("containerd://", 2)
                if container_id in containers:
                    must_delete = True
                    break
            except (KeyError, ValueError, TypeError, AttributeError):
                continue

        if must_delete:
            meta = pod["metadata"]
            cmd = [*KUBECTL, "delete", "pod", "-n", meta["namespace"], meta["name"]]
            if dry_run:
                cmd = ["echo", *cmd]

            subprocess.check_call(cmd)


if __name__ == "__main__":
    main()
