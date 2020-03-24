#!/usr/bin/python3

from common.utils import get_available_addons, get_current_arch


def print_console(addons):
    print("Available Addons:")
    for addon in addons:
        print("{:>1} {:<20} # {}".format("", addon["name"], addon["description"]))


def show_help():
    print("Usage: microk8s enable ADDON...")
    print("Enable one or more ADDON included with microk8s")
    print("Example: microk8s enable dns storage")


available_addons = get_available_addons(get_current_arch())
show_help()
print_console(available_addons)
