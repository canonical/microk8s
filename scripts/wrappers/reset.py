#!/usr/bin/python3
import click
import os
import subprocess
import shutil
import sys
import time

from common.utils import (
    get_available_addons,
    get_current_arch,
    get_status,
    snap_data,
    wait_for_ready,
    snap_common,
    is_cluster_locked,
    exit_if_no_permission,
    ensure_started,
    exit_if_no_root,
)


KUBECTL = os.path.expandvars("$SNAP/microk8s-kubectl.wrapper")


def exit_if_multinode():
    """
    Exit if we cannot get the list of nodes or if we are in a multinode cluster
    """
    cmd = [KUBECTL, "get", "no", "-o", "name"]
    res = run_silently(cmd)
    if not res:
        print("Failed to query the cluster nodes.")
        sys.exit(1)
    nodes = res.split()
    if len(nodes) > 1:
        print(
            "This is a multi-node MicroK8s deployment. Reset is applicable for single node clusters."
        )
        print("Please remove all joined nodes before calling reset.")
        sys.exit(0)


def disable_addon(repo, addon, args=None):
    """
    Try to disable an addon. Ignore any errors and/or silence any output.
    """
    if args is None:
        args = []
    wait_for_ready(timeout=30)
    script = snap_common() / "addons" / repo / "addons" / addon / "disable"
    if not script.exists():
        return

    try:
        subprocess.run([script, *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (FileNotFoundError, PermissionError, subprocess.CalledProcessError) as e:
        print(f"Ignoring error: {e}", file=sys.stderr)

    wait_for_ready(timeout=30)


def disable_addons(destroy_storage):
    """
    Iterate over all addons and disable the enabled ones.
    """
    print("Disabling all addons")

    available_addons_info = get_available_addons(get_current_arch())
    enabled, disabled = get_status(available_addons_info, True)
    for addon in available_addons_info:
        # Do not disable HA
        if addon["name"] == "ha-cluster":
            continue

        # Do not disable the community repository
        if addon["name"] == "community":
            continue

        print(f"Disabling addon : {addon['repository']}/{addon['name']}")
        # Do not disable disabled addons
        if addon in disabled:
            continue

        if (addon["name"] == "hostpath-storage" or addon["name"] == "storage") and destroy_storage:
            disable_addon(addon["repository"], f"{addon['name']}", ["destroy-storage"])
        else:
            disable_addon(addon["repository"], addon["name"])
    print("All addons are disabled.")


def cni(operation="apply"):
    """
    Apply of delete the CNI manifest of our cluster if it exists. Silence any output.
    """
    cni_yaml = f"{snap_data()}/args/cni-network/cni.yaml"
    if os.path.exists(cni_yaml):
        if operation == "apply":
            print("Setting up the CNI")
        else:
            print("Deleting the CNI")
        subprocess.run(
            [KUBECTL, operation, "-f", cni_yaml],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def clean_cluster():
    """
    Clean up the cluster by:
    1. Delete any resources left
    2. Restart so the cluster resets
    3. Delete any locks and addon binaries.
    """
    cmd = [KUBECTL, "get", "ns", "-o=name"]
    res = run_silently(cmd)
    nss = []
    if res:
        nss = res.split()
    resources = ["replicationcontrollers", "daemonsets", "deployments", "statefulsets"]
    for ns in nss:
        ns_name = ns.split("/")[-1]
        print(f"Cleaning resources in namespace {ns_name}")
        for rs in resources:
            # we remove first resources that are automatically recreated so we do not risk race conditions
            # during which a deployment for example is recreated while any tokens are missing
            cmd = [KUBECTL, "delete", "--all", rs, "-n", ns_name, "--timeout=60s"]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        remove_extra_resources(ns_name)

    print("Removing CRDs")
    cmd = [
        KUBECTL,
        "delete",
        "--all",
        "customresourcedefinitions.apiextensions.k8s.io",
        "--timeout=60s",
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    remove_priority_classes()
    remove_storage_classes()

    for ns in nss:
        ns_name = ns.split("/")[-1]
        if ns_name in ["default", "kube-public", "kube-system", "kube-node-lease"]:
            continue
        print(f"Removing {ns}")
        cmd = [KUBECTL, "delete", ns, "--timeout=60s"]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    restart_cluster()
    remove_binaries()
    reset_cert_reissue()


def remove_storage_classes():
    """
    Remove storage classes. Silence any output.
    """
    print("Removing StorageClasses")
    cmd = [KUBECTL, "get", "storageclasses", "-o=name"]
    res = run_silently(cmd)
    classes = []
    if res:
        classes = res.split()
    for cs in classes:
        if "microk8s-hostpath" in cs:
            continue
        cmd = [KUBECTL, "delete", cs, "--timeout=60s"]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def remove_priority_classes():
    """
    Remove priority classes. Silence any output.
    """
    print("Removing PriorityClasses")
    cmd = [KUBECTL, "get", "priorityclasses", "-o=name"]
    res = run_silently(cmd)
    classes = []
    if res:
        classes = res.split()
    for cs in classes:
        if "system-cluster-critical" in cs or "system-node-critical" in cs:
            continue
        cmd = [KUBECTL, "delete", cs, "--timeout=60s"]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def reset_cert_reissue():
    """
    Remove the certificate no refresh lock.
    """
    lock = snap_data() / "var" / "lock" / "no-cert-reissue"
    if lock.exists():
        cmd = f"rm -rf {lock}"
        subprocess.run(cmd.split())


def remove_binaries():
    """
    Remove binaries pulled in by addons.
    """
    bins_dir = snap_data() / "bin"
    if bins_dir.exists():
        shutil.rmtree(bins_dir)


def restart_cluster():
    """
    Restart a cluster by calling the stop and start wrappers.
    """
    print("Restarting cluster")
    cmd = [f"{os.environ['SNAP']}/microk8s-stop.wrapper"]
    subprocess.run(cmd)
    time.sleep(5)
    cmd = [f"{os.environ['SNAP']}/microk8s-start.wrapper"]
    subprocess.run(cmd)
    wait_for_ready(timeout=30)
    ensure_started()


def remove_extra_resources(ns_name):
    # Remove all resource types except the standard k8s apiservices themselves
    cmd = [KUBECTL, "api-resources", "-o", "name", "--verbs=delete", "--namespaced=true"]
    res = run_silently(cmd)
    if not res:
        return
    extra_resources = res.split()
    for rs in extra_resources:
        if rs.startswith("apiservices"):
            continue
        cmd = [KUBECTL, "delete", "--all", rs, "-n", ns_name, "--timeout=3s"]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_silently(cmd):
    result = subprocess.run(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    try:
        result.check_returncode()
    except subprocess.CalledProcessError:
        return None

    return result.stdout.decode("utf-8")


def preflight_check():
    """
    Preliminary checks to see if we can proceed with cluster reset
    """
    exit_if_no_root()
    exit_if_no_permission()
    is_cluster_locked()
    ensure_started()
    wait_for_ready(timeout=30)
    exit_if_multinode()


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--destroy-storage",
    is_flag=True,
    required=False,
    default=True,
    help="Also destroy storage. (default: false)",
)
def reset(destroy_storage):
    """
    Return the MicroK8s node to the default initial state.

    This process may take some time. All addons will be disabled and
    the configuration will be reinitialized.
    """
    preflight_check()
    disable_addons(destroy_storage)
    cni("delete")
    clean_cluster()
    cni("apply")


if __name__ == "__main__":
    reset(prog_name="microk8s reset")
