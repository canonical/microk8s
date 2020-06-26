import yaml
import json
import os
import subprocess
import sys
import time
import platform
import getpass

kubeconfig = "--kubeconfig=" + os.path.expandvars("${SNAP_DATA}/credentials/client.config")


def get_current_arch():
    # architecture mapping
    arch_mapping = {'aarch64': 'arm64', 'x86_64': 'amd64'}

    return arch_mapping[platform.machine()]


def run(*args, die=True):
    # Add wrappers to $PATH
    env = os.environ.copy()
    env["PATH"] += ":%s" % os.environ["SNAP"]
    result = subprocess.run(
        args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
    )

    try:
        result.check_returncode()
    except subprocess.CalledProcessError as err:
        if die:
            if result.stderr:
                print(result.stderr.decode("utf-8"))
            print(err)
            sys.exit(1)
        else:
            raise

    return result.stdout.decode("utf-8")


def is_cluster_ready():
    try:
        service_output = kubectl_get("all")
        node_output = kubectl_get("nodes")
        if "Ready" in node_output and "service/kubernetes" in service_output:
            return True
        else:
            return False
    except Exception:
        return False


def is_ha_enabled():
    ha_lock = os.path.expandvars("${SNAP_DATA}/var/lock/ha-cluster")
    return os.path.isfile(ha_lock)


def get_dqlite_info():
    cluster_dir = os.path.expandvars("${SNAP_DATA}/var/kubernetes/backend")
    snap_path = os.environ.get('SNAP')

    info = []

    if not is_ha_enabled():
        return info

    waits = 10
    while waits > 0:
        try:
            with open("{}/info.yaml".format(cluster_dir), mode='r') as f:
                data = yaml.load(f, Loader=yaml.FullLoader)
                out = subprocess.check_output(
                    "{snappath}/bin/dqlite -s file://{dbdir}/cluster.yaml -c {dbdir}/cluster.crt "
                    "-k {dbdir}/cluster.key -f json k8s .cluster".format(
                        snappath=snap_path, dbdir=cluster_dir
                    ).split(),
                    timeout=4,
                )
                if data['Address'] in out.decode():
                    break
                else:
                    time.sleep(5)
                    waits -= 1
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            time.sleep(2)
            waits -= 1

    if waits == 0:
        return info

    nodes = json.loads(out.decode())
    for n in nodes:
        if n["Role"] == 0:
            info.append((n["Address"], "voter"))
        if n["Role"] == 1:
            info.append((n["Address"], "standby"))
        if n["Role"] == 2:
            info.append((n["Address"], "spare"))
    return info


def is_cluster_locked():
    clusterLockFile = os.path.expandvars("${SNAP_DATA}/var/lock/clustered.lock")
    if os.path.isfile(clusterLockFile):
        print(
            "This MicroK8s deployment is acting as a node in a cluster. Please use the microk8s status on the master."
        )
        exit(0)


def wait_for_ready(wait_ready, timeout):
    start_time = time.time()
    isReady = False

    while True:
        if (timeout > 0 and (time.time() > (start_time + timeout))) or isReady:
            break
        try:
            isReady = is_cluster_ready()
        except Exception:
            time.sleep(2)

    return isReady


def exit_if_no_permission():
    user = getpass.getuser()
    # test if we can access the default kubeconfig
    clientConfigFile = os.path.expandvars("${SNAP_DATA}/credentials/client.config")
    if os.access(clientConfigFile, os.R_OK) == False:
        print("Insufficient permissions to access MicroK8s.")
        print(
            "You can either try again with sudo or add the user {} to the 'microk8s' group:".format(
                user
            )
        )
        print("")
        print("    sudo usermod -a -G microk8s {}".format(user))
        print("")
        print("The new group will be available on the user's next login.")
        exit(1)


def kubectl_get(cmd, namespace="--all-namespaces"):
    if namespace == "--all-namespaces":
        return run("kubectl", kubeconfig, "get", cmd, "--all-namespaces", die=False)
    else:
        return run("kubectl", kubeconfig, "get", cmd, "-n", namespace, die=False)


def kubectl_get_clusterroles():
    return run(
        "kubectl", kubeconfig, "get", "clusterroles", "--show-kind", "--no-headers", die=False
    )


def get_available_addons(arch):
    addon_dataset = os.path.expandvars("${SNAP}/addon-lists.yaml")
    available = []
    with open(addon_dataset, 'r') as file:
        # The FullLoader parameter handles the conversion from YAML
        # scalar values to Python the dictionary format
        addons = yaml.load(file, Loader=yaml.FullLoader)
        for addon in addons["microk8s-addons"]["addons"]:
            if arch in addon["supported_architectures"]:
                available.append(addon)

    available = sorted(available, key=lambda k: k['name'])
    return available


def get_addon_by_name(addons, name):
    filtered_addon = []
    for addon in addons:
        if name == addon["name"]:
            filtered_addon.append(addon)
    return filtered_addon
