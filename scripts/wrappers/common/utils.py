import getpass
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import click
import yaml

kubeconfig = "--kubeconfig=" + os.path.expandvars("${SNAP_DATA}/credentials/client.config")


def get_current_arch():
    # architecture mapping
    arch_mapping = {'aarch64': 'arm64', 'x86_64': 'amd64'}

    return arch_mapping[platform.machine()]


def snap_data() -> Path:
    try:
        return Path(os.environ['SNAP_DATA'])
    except KeyError:
        return Path('/var/snap/microk8s/current')


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
        # Make sure to compare with the word " Ready " with spaces.
        if " Ready " in node_output and "service/kubernetes" in service_output:
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
    if (snap_data() / 'var/lock/clustered.lock').exists():
        click.echo('This MicroK8s deployment is acting as a node in a cluster.')
        click.echo('Please use the master node.')
        sys.exit(1)


def wait_for_ready(timeout):
    start_time = time.time()

    while True:
        if is_cluster_ready():
            return True
        elif timeout and time.time() > start_time + timeout:
            return False
        else:
            time.sleep(2)


def exit_if_stopped():
    stoppedLockFile = os.path.expandvars("${SNAP_DATA}/var/lock/stopped.lock")
    if os.path.isfile(stoppedLockFile):
        print("microk8s is not running, try microk8s start")
        exit(0)


def exit_if_no_permission():
    user = getpass.getuser()
    # test if we can access the default kubeconfig
    clientConfigFile = os.path.expandvars("${SNAP_DATA}/credentials/client.config")
    if not os.access(clientConfigFile, os.R_OK):
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


def ensure_started():
    if (snap_data() / 'var/lock/stopped.lock').exists():
        click.echo('microk8s is not running, try microk8s start', err=True)
        sys.exit(1)


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


def is_service_expected_to_start(service):
    """
    Check if a service is supposed to start
    :param service: the service name
    :return: True if the service is meant to start
    """
    lock_path = os.path.expandvars("${SNAP_DATA}/var/lock")
    lock = "{}/{}".format(lock_path, service)
    return os.path.exists(lock_path) and not os.path.isfile(lock)


def set_service_expected_to_start(service, start=True):
    """
    Check if a service is not expected to start.
    :param service: the service name
    :param start: should the service start or not
    """
    lock_path = os.path.expandvars("${SNAP_DATA}/var/lock")
    lock = "{}/{}".format(lock_path, service)
    if start:
        os.remove(lock)
    else:
        fd = os.open(lock, os.O_CREAT, mode=0o700)
        os.close(fd)


def check_help_flag(addons: list) -> bool:
    """Checks to see if a help message needs to be printed for an addon.

    Not all addons check for help flags themselves. Until they do, intercept
    calls to print help text and print out a generic message to that effect.
    """
    addon = addons[0]
    if any(arg in addons for arg in ('-h', '--help')) and addon != 'kubeflow':
        print("Addon %s does not yet have a help message." % addon)
        print("For more information about it, visit https://microk8s.io/docs/addons")
        return True
    return False


def xable(action: str, addons: list, xabled_addons: list):
    """Enables or disables the given addons.

    Collated into a single function since the logic is identical other than
    the script names.
    """
    actions = Path(__file__).absolute().parent / "../../../actions"
    existing_addons = {sh.with_suffix('').name[7:] for sh in actions.glob('enable.*.sh')}

    # Backwards compatibility with enabling multiple addons at once, e.g.
    # `microk8s.enable foo bar:"baz"`
    if all(a.split(':')[0] in existing_addons for a in addons) and len(addons) > 1:
        for addon in addons:
            if addon in xabled_addons and addon != 'kubeflow':
                click.echo("Addon %s is already %sd." % (addon, action))
            else:
                addon, *args = addon.split(':')
                wait_for_ready(timeout=30)
                subprocess.run([str(actions / ('%s.%s.sh' % (action, addon)))] + args)
                wait_for_ready(timeout=30)

    # The new way of xabling addons, that allows for unix-style argument passing,
    # such as `microk8s.enable foo --bar`.
    else:
        addon, *args = addons[0].split(':')

        if addon in xabled_addons and addon != 'kubeflow':
            click.echo("Addon %s is already %sd." % (addon, action))
            sys.exit(0)

        if addon not in existing_addons:
            click.echo("Nothing to do for `%s`." % addon, err=True)
            sys.exit(1)

        if args and addons[1:]:
            click.echo(
                "Can't pass string arguments and flag arguments simultaneously!\n"
                "{0} an addon with only one argument style at a time:\n"
                "\n"
                "    microk8s {1} foo:'bar'\n"
                "or\n"
                "    microk8s {1} foo --bar\n".format(action.title(), action)
            )
            sys.exit(1)

        wait_for_ready(timeout=30)
        script = [str(actions / ('%s.%s.sh' % (action, addon)))]
        if args:
            subprocess.run(script + args)
        else:
            subprocess.run(script + list(addons[1:]))

        wait_for_ready(timeout=30)
