import getpass
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
import logging

import click
import yaml

LOG = logging.getLogger(__name__)

kubeconfig = "--kubeconfig=" + os.path.expandvars("${SNAP_DATA}/credentials/client.config")


def get_current_arch():
    # architecture mapping
    arch_mapping = {"aarch64": "arm64", "armv7l": "armhf", "x86_64": "amd64", "s390x": "s390x"}

    return arch_mapping[platform.machine()]


def snap_data() -> Path:
    try:
        return Path(os.environ["SNAP_DATA"])
    except KeyError:
        return Path("/var/snap/microk8s/current")


def snap_common() -> Path:
    try:
        return Path(os.environ["SNAP_COMMON"])
    except KeyError:
        return Path("/var/snap/microk8s/common")


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
    snap_path = os.environ.get("SNAP")

    info = []

    if not is_ha_enabled():
        return info

    waits = 10
    while waits > 0:
        try:
            with open("{}/info.yaml".format(cluster_dir), mode="r") as f:
                data = yaml.safe_load(f)
                out = subprocess.check_output(
                    "{snappath}/bin/dqlite -s file://{dbdir}/cluster.yaml -c {dbdir}/cluster.crt "
                    "-k {dbdir}/cluster.key -f json k8s .cluster".format(
                        snappath=snap_path, dbdir=cluster_dir
                    ).split(),
                    timeout=4,
                    stderr=subprocess.DEVNULL,
                )
                if data["Address"] in out.decode():
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
    if (snap_data() / "var/lock/clustered.lock").exists():
        click.echo("This MicroK8s deployment is acting as a node in a cluster.")
        click.echo("Please use the master node.")
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
        print("    sudo chown -f -R $USER ~/.kube")
        print("")
        print(
            "After this, reload the user groups either via a reboot or by running 'newgrp microk8s'."
        )
        exit(1)


def ensure_started():
    if (snap_data() / "var/lock/stopped.lock").exists():
        click.echo("microk8s is not running, try microk8s start", err=True)
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
    available = []
    for dir in os.listdir(snap_common() / "addons"):
        try:
            addons_yaml = snap_common() / "addons" / dir / "addons.yaml"
            with open(addons_yaml, "r") as fin:
                addons = yaml.safe_load(fin)

            for addon in addons["microk8s-addons"]["addons"]:
                if arch in addon["supported_architectures"]:
                    available.append(
                        {
                            **addon,
                            "repository": dir,
                        }
                    )
        except Exception:
            LOG.exception("could not load addons from %s", addons_yaml)

    available = sorted(available, key=lambda k: (k["repository"], k["name"]))
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
    if any(arg in addons for arg in ("-h", "--help")):
        print("Addon %s does not yet have a help message." % addon)
        print("For more information about it, visit https://microk8s.io/docs/addons")
        return True
    return False


def parse_xable_addon_args(addon_args: list, available_addons: list):
    """
    Parse the list of addons passed into the microk8s enable or disable commands.
    Further, it will infer the repository name for addons when possible.
    If any errors are encountered, we print them to stderr and exit.

    :param addon_args: The parameters passed to the microk8s enable command
    :param available_addons: List of available addons as (repository_name, addon_name) tuples

    Handles the following cases:
    - microk8s enable foo bar:--baz      # enable many addons, inline arguments
    - microk8s enable bar --baz          # enable one addon, unix style command line arguments

    :return: a list of (repository_name, addon_name, args) tuples
    """

    # Backwards compatibility with enabling multiple addons at once, e.g.
    # `microk8s.enable foo bar:"baz"`
    available_addon_names = [addon_name for (_, addon_name) in available_addons]
    addon_names = [arg.split(":")[0] for arg in addon_args]
    if set(addon_names) < set(available_addon_names):
        return [parse_xable_single_arg(addon_arg, available_addons) for addon_arg in addon_args]

    # The new way of xabling addons, that allows for unix-style argument passing,
    # such as `microk8s.enable foo --bar`.
    repository_name, addon_name, args = parse_xable_single_arg(addon_args[0], available_addons)
    if args and addon_args[1:]:
        click.echo(
            "Can't pass string arguments and flag arguments simultaneously!\n"
            "Enable or disable addons with only one argument style at a time:\n"
            "\n"
            "    microk8s enable foo:'bar'\n"
            "or\n"
            "    microk8s enable foo --bar\n"
        )
        sys.exit(1)

    return [(repository_name, addon_name, addon_args[1:])]


def parse_xable_single_arg(addon_arg: str, available_addons: list):
    """
    Parse an addon arg of the following form: `(repository_name/)addon_name(:args)`
    It will automatically infer the repository name if not specified. If multiple repositories
    are found for the addon, we print an error and exit.

    :param addon_arg: A parameter passed to the microk8s enable command
    :param available_addons: List of available addons as (repository_name, addon_name) tuples

    :return: a (repository_name, addon_name, args) tuple
    """
    addon_name, *args = addon_arg.split(":")
    parts = addon_name.split("/")
    if len(parts) == 2:
        return (parts[0], parts[1], args)
    elif len(parts) == 1:
        matching_addons = list(filter((lambda x: x[1] == addon_name), available_addons))
        matching_repositories = [x[0] for x in matching_addons]
        if len(matching_repositories) == 0:
            click.echo("Addon {} was not found in any repository".format(addon_name), err=True)
            sys.exit(1)
        elif len(matching_repositories) == 1:
            click.echo(
                "Infer repository {} for addon {}".format(matching_repositories[0], addon_name),
                err=True,
            )
            return (matching_repositories[0], addon_name, args)
        else:
            click.echo(
                "Addon {} exists in more than repository. Please explicitly specify\n"
                "the repository using any of:\n".format(addon_name),
                err=True,
            )
            for repository in matching_repositories:
                click.echo("    {}/{}".format(repository, addon_name), err=True)
            click.echo("", err=True)
            sys.exit(1)

    else:
        click.echo("Invalid addon name {}".format(addon_name))
        sys.exit(1)


def xable(action: str, addon_args: list):
    """Enables or disables the given addons.

    Collated into a single function since the logic is identical other than
    the script names.

    :param action: "enable" or "disable"
    :param addons: List of addons to enable. Each addon may be prefixed with `repository/`
                   to specify which addon repository it will be sourced from.
    """
    available_addons_info = get_available_addons(get_current_arch())
    enabled_addons_info, disabled_addons_info = get_status(available_addons_info, True)
    if action == "enable":
        xabled_addons_info = enabled_addons_info
    elif action == "disable":
        xabled_addons_info = disabled_addons_info
    else:
        click.echo("Invalid action {}. Only enable and disable are supported".format(action))
        sys.exit(1)

    # available_addons is a list of (repository_name, addon_name) tuples for all available addons
    available_addons = [(addon["repository"], addon["name"]) for addon in available_addons_info]
    # xabled_addons is a list (repository_name, addon_name) tuples of already xabled addons
    xabled_addons = [(addon["repository"], addon["name"]) for addon in xabled_addons_info]

    addons = parse_xable_addon_args(addon_args, available_addons)

    for repository_name, addon_name, args in addons:
        if (repository_name, addon_name) in xabled_addons:
            click.echo("Addon {}/{} is already {}d".format(repository_name, addon_name, action))
            continue

        wait_for_ready(timeout=30)
        p = subprocess.run(
            [snap_common() / "addons" / repository_name / "addons" / addon_name / action, *args]
        )
        if p.returncode:
            sys.exit(p.returncode)
        wait_for_ready(timeout=30)


def is_enabled(addon, item):
    if addon in item:
        return True
    else:
        filepath = os.path.expandvars(addon)
        return os.path.isfile(filepath)


def get_status(available_addons, isReady):
    enabled = []
    disabled = []
    if isReady:
        # 'all' does not include ingress
        kube_output = kubectl_get("all,ingress")
        cluster_output = kubectl_get_clusterroles()
        kube_output = kube_output + cluster_output
        for addon in available_addons:
            found = False
            for row in kube_output.split("\n"):
                if is_enabled(addon["check_status"], row):
                    enabled.append(addon)
                    found = True
                    break
            if not found:
                disabled.append(addon)

    return enabled, disabled
