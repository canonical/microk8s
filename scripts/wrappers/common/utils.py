import yaml
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
