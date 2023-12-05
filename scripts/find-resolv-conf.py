#!/usr/bin/env python3

import ipaddress
import re

import click


# https://regex101.com/r/RWZH94/1
NAMESERVER_REGEX = r"^\s*nameserver\s+(\S*)\s*$"

DEFAULT_RESOLV_CONFS = [
    "/etc/resolv.conf",
    "/run/systemd/resolve/resolv.conf",
]


def safe_is_non_loopback_address(address: str):
    """
    Return true if the given address is a valid non loopback address. Returns
    false if the address is loopback or invalid
    """
    try:
        return not ipaddress.ip_address(address).is_loopback
    except ValueError:
        # NOTE(neoaggelos): https://github.com/canonical/microk8s/issues/4327
        # Python 3.8 fails with scoped IPv6 address, e.g. "fe80::5054:ff:fe00:b61d%2"
        # Try to remove the scope suffix, and accept if value is an IPv6 address
        if "%" not in address:
            return False

        try:
            ip = ipaddress.ip_address(address[: address.find("%")])
            return ip.version == 6 and not ip.is_loopback
        except (ValueError, IndexError):
            return False


def find_resolv_conf_with_non_loopback_address(resolv_confs: list):
    """
    Given a list of resolv.conf file paths, return the first one that contains non-loopback
    upstream nameservers.
    """
    for path in resolv_confs:
        try:
            with open(path) as fin:
                contents = fin.read()

            nameservers = re.findall(NAMESERVER_REGEX, contents, re.MULTILINE)

            if nameservers and all(map(safe_is_non_loopback_address, nameservers)):
                return path
        except (OSError, ValueError):
            # ignore invalid resolv.conf files
            pass


@click.command("find-resolv-conf")
@click.argument("resolv_confs", nargs=-1)
def main(resolv_confs):
    """
    find-resolv-conf looks in the system for a resolv.conf file that contains non-loopback
    upstream nameservers. If there are any, the first one found is printed to stdout.

    Paths to resolv.conf files may be given as arguments. By default, known system locations
    defined in DEFAULT_RESOLV_CONFS are checked.

    If no resolv.conf file with non-loopback nameservers is found, nothing is printed to stdout.
    """
    path = find_resolv_conf_with_non_loopback_address(resolv_confs or DEFAULT_RESOLV_CONFS)
    if path:
        print(path)


if __name__ == "__main__":
    main()
