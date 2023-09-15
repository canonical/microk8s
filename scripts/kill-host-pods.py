#!/usr/bin/env python3

import json
import subprocess
import os
from pathlib import Path

import click

CTR = os.path.expandvars("$SNAP/microk8s-ctr.wrapper")
SNAP = os.getenv("SNAP")
SNAP_DATA = os.getenv("SNAP_DATA")
SNAP_DATA_BASE = os.path.abspath(f"{SNAP_DATA}/..")
SNAP_DATA_CURRENT = os.path.abspath(f"{SNAP_DATA_BASE}/current")
SNAP_COMMON = os.path.abspath(f"{SNAP_DATA_BASE}/common")
KUBECTL = [f"{SNAP}/kubectl", f"--kubeconfig={SNAP_DATA}/credentials/kubelet.config"]


def post_filter_has_known_containers(pod, containers: list) -> bool:
    """
    Return true if any of the container IDs on the pod match the list of
    containers passed on the second argument.
    """
    for container in pod["status"]["containerStatuses"] or []:
        try:
            _, container_id = container["containerID"].split("containerd://", 2)
            if container_id in containers:
                return True
        except (KeyError, ValueError, TypeError, AttributeError):
            continue

    return False


def post_filter_has_snap_data_mounts(pod) -> bool:
    """
    Return true if a pod definition contains any volumes that mount paths
    from `/var/snap/microk8s/current/...`, e.g. CNI pods
    """
    for volume in pod["spec"].get("volumes", []):
        hostpath_volume = volume.get("hostPath", {})
        host_path = hostpath_volume.get("path", "")
        if not host_path:
            return False
        if host_path.startswith(SNAP_DATA_CURRENT):
            return True

        # handle the case where a symlink to a SNAP_DATA path is used
        try:
            resolved = Path(host_path).resolve().as_posix()
            if resolved.startswith(SNAP_DATA_BASE) and not resolved.startswith(SNAP_COMMON):
                return True
        except OSError:
            pass

    return False


def post_filter_has_owner(pod: dict):
    """
    Return true if a pod definition has an ownerReference (i.e. is it managed by a
    Deployment or a DaemonSet)
    """
    owner_references = pod["metadata"].get("ownerReferences") or []
    return len(owner_references) > 0


@click.command("kill-host-pods")
@click.argument("selector", nargs=-1)
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--with-snap-data-mounts", is_flag=True, default=False)
@click.option("--with-owner", is_flag=True, default=False)
def main(selector: list, dry_run: bool, with_snap_data_mounts: bool, with_owner: bool):
    """
    Delete pods running on the local node based on Kubernetes selectors.

    Example usage:

    $ ./kill-host-pods.py -- -n kube-system -l k8s-app=calico-node
    $ ./kill-host-pods.py --with-snap-data-mounts -- -n kube-system
    $ ./kill-host-pods.py --with-snap-data-mounts -- -A
    """
    containers = subprocess.check_output([CTR, "container", "ls", "-q"]).decode().split("\n")
    out = subprocess.check_output([*KUBECTL, "get", "pod", "-o", "json", *selector])

    pods = json.loads(out)
    for pod in pods["items"]:
        if not post_filter_has_known_containers(pod, containers):
            continue
        if with_snap_data_mounts and not post_filter_has_snap_data_mounts(pod):
            continue
        if with_owner and not post_filter_has_owner(pod):
            continue

        meta = pod["metadata"]
        cmd = [*KUBECTL, "delete", "pod", "-n", meta["namespace"], meta["name"]]
        if dry_run:
            cmd = ["echo", *cmd]

        subprocess.check_call(cmd)


if __name__ == "__main__":
    main()
