#!/usr/bin/python3
import os
import argparse

from common.utils import (
    exit_if_no_permission,
    exit_if_stopped,
    is_cluster_locked,
    is_ha_enabled,
    get_dqlite_info,
    wait_for_ready,
    is_cluster_ready,
    get_available_addons,
    get_current_arch,
    get_addon_by_name,
    kubectl_get,
    kubectl_get_clusterroles,
)


def is_enabled(addon, item):
    if addon in item:
        return True
    else:
        filepath = os.path.expandvars(addon)
        return os.path.isfile(filepath)

    return False


def print_short(isReady, enabled_addons, disabled_addons):
    if isReady:
        print("microk8s is running")
        print("addons:")
        if enabled_addons and len(enabled_addons) > 0:
            for enabled in enabled_addons:
                print("{}: enabled".format(enabled["name"]))
        if disabled_addons and len(disabled_addons) > 0:
            for disabled in disabled_addons:
                print("{}: disabled".format(disabled["name"]))
    else:
        print("microk8s is not running. Use microk8s inspect for a deeper inspection.")


def print_pretty(isReady, enabled_addons, disabled_addons):
    console_formatter = "{:>3} {:<20} # {}"
    if isReady:
        print("microk8s is running")
        if not is_ha_enabled():
            print("high-availability: no")
        else:
            info = get_dqlite_info()
            if ha_cluster_formed(info):
                print("high-availability: yes")
            else:
                print("high-availability: no")

            masters = "none"
            standby = "none"
            for node in info:
                if node[1] == "voter":
                    if masters == "none":
                        masters = "{}".format(node[0])
                    else:
                        masters = "{} {}".format(masters, node[0])
                if node[1] == "standby":
                    if standby == "none":
                        standby = "{}".format(node[0])
                    else:
                        standby = "{} {}".format(standby, node[0])

            print("{:>2}{} {}".format("", "datastore master nodes:", masters))
            print("{:>2}{} {}".format("", "datastore standby nodes:", standby))

        print("addons:")
        if enabled_addons and len(enabled_addons) > 0:
            print('{:>2}{}'.format("", "enabled:"))
            for enabled in enabled_addons:
                print(console_formatter.format("", enabled["name"], enabled["description"]))
        if disabled_addons and len(disabled_addons) > 0:
            print('{:>2}{}'.format("", "disabled:"))
            for disabled in disabled_addons:
                print(console_formatter.format("", disabled["name"], disabled["description"]))
    else:
        print("microk8s is not running. Use microk8s inspect for a deeper inspection.")


def print_short_yaml(isReady, enabled_addons, disabled_addons):
    print("microk8s:")
    print("{:>2}{} {}".format("", "running:", isReady))

    if isReady:
        print("addons:")
        for enabled in enabled_addons:
            print("  {}: enabled".format(enabled["name"]))

        for disabled in disabled_addons:
            print("  {}: disabled".format(disabled["name"]))
    else:
        print(
            "{:>2} {} {}".format(
                "",
                "message:",
                "microk8s is not running. Use microk8s inspect for a deeper inspection.",
            )
        )


def print_yaml(isReady, enabled_addons, disabled_addons):
    print("microk8s:")
    print("{:>2}{} {}".format("", "running:", isReady))

    print("{:>2}".format("high-availability:"))
    ha_enabled = is_ha_enabled()
    print("{:>2}{} {}".format("", "enabled:", ha_enabled))
    if ha_enabled:
        info = get_dqlite_info()
        print("{:>2}{}".format("", "nodes:"))
        for node in info:
            print("{:>6}address: {:<1}".format("- ", node[0]))
            print("{:>6}role: {:<1}".format("", node[1]))

    if isReady:
        print("{:>2}".format("addons:"))
        for enabled in enabled_addons:
            print("{:>4}name: {:<1}".format("- ", enabled["name"]))
            print("{:>4}description: {:<1}".format("", enabled["description"]))
            print("{:>4}version: {:<1}".format("", enabled["version"]))
            print("{:>4}status: enabled".format(""))

        for disabled in disabled_addons:
            print("{:>4}name: {:<1}".format("- ", disabled["name"]))
            print("{:>4}description: {:<1}".format("", disabled["description"]))
            print("{:>4}version: {:<1}".format("", disabled["version"]))
            print("{:>4}status: disabled".format(""))
    else:
        print(
            "{:>2} {} {}".format(
                "",
                "message:",
                "microk8s is not running. Use microk8s inspect for a deeper inspection.",
            )
        )


def print_addon_status(enabled):
    if len(enabled) > 0:
        print("enabled")
    else:
        print("disabled")


def get_status(available_addons, isReady):
    enabled = []
    disabled = []
    if isReady:
        kube_output = kubectl_get("all")
        cluster_output = kubectl_get_clusterroles()
        kube_output = kube_output + cluster_output
        for addon in available_addons:
            found = False
            for row in kube_output.split('\n'):
                if is_enabled(addon["check_status"], row):
                    enabled.append(addon)
                    found = True
                    break
            if not found:
                disabled.append(addon)

    return enabled, disabled


def ha_cluster_formed(info):
    voters = 0
    for node in info:
        if node[1] == "voter":
            voters += 1
    ha_formed = False
    if voters > 2:
        ha_formed = True
    return ha_formed


if __name__ == '__main__':
    exit_if_no_permission()
    exit_if_stopped()
    is_cluster_locked()

    # initiate the parser with a description
    parser = argparse.ArgumentParser(
        description='Microk8s cluster status check.', prog='microk8s status'
    )
    parser.add_argument(
        "--format",
        help="print cluster and addon status, output can be in yaml, pretty or short",
        default="pretty",
        choices={"pretty", "yaml", "short"},
    )
    parser.add_argument(
        "-w", "--wait-ready", action='store_true', help="wait until the cluster is in ready state"
    )
    parser.add_argument(
        "-t",
        "--timeout",
        help="specify a timeout in seconds when waiting for the cluster to be ready.",
        type=int,
        default=0,
    )
    parser.add_argument("-a", "--addon", help="check the status of an addon.", default="all")
    parser.add_argument(
        "--yaml", action='store_true', help="DEPRECATED, use '--format yaml' instead"
    )

    # read arguments from the command line
    args = parser.parse_args()

    wait_ready = args.wait_ready
    timeout = args.timeout
    yaml_short = args.yaml

    if wait_ready:
        isReady = wait_for_ready(timeout)
    else:
        isReady = is_cluster_ready()

    available_addons = get_available_addons(get_current_arch())

    if args.addon != "all":
        available_addons = get_addon_by_name(available_addons, args.addon)

    enabled, disabled = get_status(available_addons, isReady)

    if args.addon != "all":
        print_addon_status(enabled)
    else:
        if args.format == "yaml":
            print_yaml(isReady, enabled, disabled)
        elif args.format == "short":
            print_short(isReady, enabled, disabled)
        else:
            if yaml_short:
                print_short_yaml(isReady, enabled, disabled)
            else:
                print_pretty(isReady, enabled, disabled)
