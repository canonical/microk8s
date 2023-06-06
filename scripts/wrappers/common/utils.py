import fcntl
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

from common.cluster.utils import (
    try_set_file_permissions,
    is_strict,
)

LOG = logging.getLogger(__name__)

KUBECTL = os.path.expandvars("$SNAP/microk8s-kubectl.wrapper")


def get_current_arch():
    # architecture mapping
    arch_mapping = {
        "aarch64": "arm64",
        "armv7l": "armhf",
        "x86_64": "amd64",
        "s390x": "s390x",
        "ppc64le": "ppc64le",
        "ppc64el": "ppc64le",
    }

    return arch_mapping[platform.machine()]


def snap() -> Path:
    try:
        return Path(os.environ["SNAP"])
    except KeyError:
        return Path("/snap/microk8s/current")


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


def is_cluster_ready(with_ready_node=True):
    try:
        return "service/kubernetes" in kubectl_get("all") and (
            not with_ready_node or " Ready " in kubectl_get("nodes")
        )
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


def get_etcd_info():
    kube_apiserver_args = os.path.expandvars("${SNAP_DATA}/args/kube-apiserver")
    with open(kube_apiserver_args, "r") as f:
        kube_apiserver_args_content = f.read()
        etcd_endpoints = []
        for line in kube_apiserver_args_content.split("\n"):
            if "etcd-servers" in line:
                server_url = get_server_urls(line)
                # list all etcd endpointss
                for endpoint in server_url.split(","):
                    if "//" in endpoint:
                        ip_port = endpoint.split("//")[1]
                        etcd_endpoints.append(ip_port)
                break

    return etcd_endpoints


def get_server_urls(args):
    server_url = None
    parts = args.split("=")
    if len(parts) == 2:
        # Argument has an equals sign, e.g. "--etcd-servers=http://10.0.0.1:2379"
        server_url = parts[1]
    elif len(parts) == 1:
        # Argument has a space, e.g. "--etcd-servers http://10.0.0.1:2379"
        server_url = args.split("--etcd-servers")[1].strip()
    return server_url


def is_external_etcd():
    kube_apiserver_args = os.path.expandvars("${SNAP_DATA}/args/kube-apiserver")
    with open(kube_apiserver_args, "r") as f:
        kube_apiserver_args_content = f.read()
        for line in kube_apiserver_args_content.split("\n"):
            if "var/kubernetes/backend/kine.sock" in line:
                return False
    return True


def is_cluster_locked():
    if (snap_data() / "var/lock/clustered.lock").exists():
        click.echo("This MicroK8s deployment is acting as a node in a cluster.")
        click.echo("Please use the master node.")
        sys.exit(1)


def wait_for_ready(timeout, with_ready_node=True):
    start_time = time.time()
    end_time = start_time + timeout

    while True:
        if is_cluster_ready(with_ready_node=with_ready_node):
            return True
        elif timeout and time.time() > end_time:
            return False
        else:
            time.sleep(2)


def exit_if_no_root():
    """
    Exit if the user is not root
    """
    if not os.geteuid() == 0:
        click.echo(
            "Elevated permissions is needed for this operation. Please run this command with sudo."
        )
        exit(50)


def exit_if_stopped():
    stoppedLockFile = os.path.expandvars("${SNAP_DATA}/var/lock/stopped.lock")
    if os.path.isfile(stoppedLockFile):
        print("microk8s is not running, try microk8s start")
        exit(0)


def exit_if_no_permission():
    user = getpass.getuser()
    # test if we can access the default kubeconfig
    client_config_file = os.path.expandvars("${SNAP_DATA}/credentials/client.config")
    if not os.access(client_config_file, os.R_OK):
        print("Insufficient permissions to access MicroK8s.")
        print(
            "You can either try again with sudo or add the user {} to the 'microk8s' group:".format(
                user
            )
        )
        print("")
        print("    sudo usermod -a -G microk8s {}".format(user))
        print("    sudo chown -R $USER ~/.kube")
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
        return run(KUBECTL, "get", cmd, "--all-namespaces", die=False)
    else:
        return run(KUBECTL, "get", cmd, "-n", namespace, die=False)


def kubectl_get_clusterroles():
    return run(
        KUBECTL,
        "get",
        "clusterroles",
        "--show-kind",
        "--no-headers",
        die=False,
    )


def is_community_addon(arch, addon_name):
    """
    Check if an addon is part of the community repo.

    :param arch: architecture of the addon we are looking for
    :param addon_name: name of the addon we are looking for
    :return: True if the addon is in the community repo
    """
    try:
        addons_yaml = f"{os.environ['SNAP']}/addons/community/addons.yaml"
        with open(addons_yaml, "r") as fin:
            addons = yaml.safe_load(fin)

        for addon in addons["microk8s-addons"]["addons"]:
            if arch in addon["supported_architectures"]:
                if addon_name == addon["name"]:
                    return True
    except Exception:
        LOG.exception("could not load addons from %s", addons_yaml)

    return False


def get_available_addons(arch):
    available = []
    strict = is_strict()
    for dir in os.listdir(snap_common() / "addons"):
        try:
            addons_yaml = snap_common() / "addons" / dir / "addons.yaml"
            with open(addons_yaml, "r") as fin:
                addons = yaml.safe_load(fin)

            for addon in addons["microk8s-addons"]["addons"]:
                if arch not in addon["supported_architectures"]:
                    continue

                if "confinement" in addon:
                    if strict and "strict" not in addon["confinement"]:
                        continue
                    if not strict and "classic" not in addon["confinement"]:
                        continue

                available.append({**addon, "repository": dir})

        except Exception:
            LOG.exception("could not load addons from %s", addons_yaml)

    available = sorted(available, key=lambda k: (k["repository"], k["name"]))
    return available


def get_addon_by_name(addons, name):
    filtered_addon = []

    parts = name.split("/")
    if len(parts) == 1:
        repo_name, addon_name = None, parts[0]
    elif len(parts) == 2:
        repo_name, addon_name = parts[0], parts[1]
    else:
        # just fallback to the addon name
        repo_name, addon_name = None, name

    for addon in addons:
        if addon_name == addon["name"] and (repo_name == addon["repository"] or not repo_name):
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
    if any(help_arg in addons for help_arg in ("-h", "--help")):
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
    :param available_addons: List of available addons as (repo_name, addon_name) tuples

    Handles the following cases:
    - microk8s enable foo bar:--baz      # enable many addons, inline arguments
    - microk8s enable bar --baz          # enable one addon, unix style command line arguments

    :return: a list of (repo_name, addon_name, args) tuples
    """

    # Backwards compatibility with enabling multiple addons at once, e.g.
    # `microk8s.enable foo bar:"baz"`
    available_addon_names = [addon_name for (_, addon_name) in available_addons]
    available_addon_names += [
        "/".join([repo_name, addon_name]) for (repo_name, addon_name) in available_addons
    ]
    addon_names = [arg.split(":")[0] for arg in addon_args]
    if set(addon_names) < set(available_addon_names):
        return [parse_xable_single_arg(addon_arg, available_addons) for addon_arg in addon_args]

    # The new way of xabling addons, that allows for unix-style argument passing,
    # such as `microk8s.enable foo --bar`.
    repo_name, addon_name, args = parse_xable_single_arg(addon_args[0], available_addons)
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

    return [(repo_name, addon_name, addon_args[1:])]


def parse_xable_single_arg(addon_arg: str, available_addons: list):
    """
    Parse an addon arg of the following form: `(repo_name/)addon_name(:args)`
    It will automatically infer the repository name if not specified. If multiple repositories
    are found for the addon, we print an error and exit.

    :param addon_arg: A parameter passed to the microk8s enable command
    :param available_addons: List of available addons as (repo_name, addon_name) tuples

    :return: a (repo_name, addon_name, args) tuple
    """
    addon_name, *args = addon_arg.split(":")
    parts = addon_name.split("/")
    if len(parts) == 2:
        return (parts[0], parts[1], args)
    elif len(parts) == 1:
        matching_repos = [repo for (repo, addon) in available_addons if addon == addon_name]
        if len(matching_repos) == 0:
            click.echo("Addon {} was not found in any repository".format(addon_name), err=True)
            if is_community_addon(get_current_arch(), addon_name):
                click.echo(
                    "To use the community maintained flavor enable the respective repository:"
                )
                click.echo("")
                click.echo("    microk8s enable community")
                click.echo("")

            sys.exit(1)
        elif len(matching_repos) == 1:
            click.echo(
                "Infer repository {} for addon {}".format(matching_repos[0], addon_name), err=True
            )
            return (matching_repos[0], addon_name, args)
        else:
            click.echo(
                "Addon {} exists in more than repository. Please explicitly specify\n"
                "the repository using any of:\n".format(addon_name),
                err=True,
            )
            for repo in matching_repos:
                click.echo("    {}/{}".format(repo, addon_name), err=True)
            click.echo("", err=True)
            sys.exit(1)

    else:
        click.echo("Invalid addon name {}".format(addon_name))
        sys.exit(1)


def xable(action: str, addon_args: list):
    if os.getenv("MICROK8S_ADDONS_SKIP_LOCK") == "1":
        unprotected_xable(action, addon_args)
    else:
        protected_xable(action, addon_args)


def protected_xable(action: str, addon_args: list):
    """
    Get an exclusive lock file and then perform enable/disable of addons.

    Ensure that the lock file is always unlocked on exit.
    """

    lock_file_path = snap_data() / "var/lock/.microk8s-addon-lock"
    with open(lock_file_path, "w") as f:
        # set file permissions so non-root users do not fail
        try:
            try_set_file_permissions(lock_file_path)
        except OSError:
            pass

        try:
            fcntl.lockf(f, fcntl.LOCK_EX)

            # NOTE(neoaggelos): We now have the lock, ensure any recursive
            # invocations will not deadlock. One example is addons that
            # enable other addons as requirements.
            #
            # See the relevant check in xable().
            os.environ["MICROK8S_ADDONS_SKIP_LOCK"] = "1"

            unprotected_xable(action, addon_args)
        finally:
            fcntl.lockf(f, fcntl.LOCK_UN)


def unprotected_xable(action: str, addon_args: list):
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

    # available_addons is a list of (repo_name, addon_name) tuples for all available addons
    available_addons = [(addon["repository"], addon["name"]) for addon in available_addons_info]
    # xabled_addons is a list (repo_name, addon_name) tuples of already xabled addons
    xabled_addons = [(addon["repository"], addon["name"]) for addon in xabled_addons_info]

    addons = parse_xable_addon_args(addon_args, available_addons)
    if len(addons) > 1:
        click.echo(
            "WARNING: Do not enable or disable multiple addons in one command.\n"
            "         This form of chained operations on addons will be DEPRECATED in the future.\n"
            f"         Please, {action} one addon at a time: 'microk8s {action} <addon>'"
        )

    for repo_name, addon_name, args in addons:
        if (repo_name, addon_name) not in available_addons:
            click.echo("Addon {}/{} not found".format(repo_name, addon_name))
            continue
        if (repo_name, addon_name) in xabled_addons:
            click.echo("Addon {}/{} is already {}d".format(repo_name, addon_name, action))
            continue

        wait_for_ready(timeout=30, with_ready_node=False)
        p = subprocess.run(
            [snap_common() / "addons" / repo_name / "addons" / addon_name / action, *args]
        )
        if p.returncode:
            sys.exit(p.returncode)
        wait_for_ready(timeout=30, with_ready_node=False)


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


def is_within_directory(directory, target):
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)

    prefix = os.path.commonprefix([abs_directory, abs_target])

    return prefix == abs_directory


def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        if not is_within_directory(path, member_path):
            raise Exception("Attempted Path Traversal in Tar File")

    tar.extractall(path, members, numeric_owner=numeric_owner)
