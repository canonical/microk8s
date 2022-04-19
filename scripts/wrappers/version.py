#!/usr/bin/env python3

import click
import json
from common.utils import snap_data
from common.utils import run


VERSIONS_FILE = snap_data() / "versions.json"
VERSIONS = None


def get_upstream_version(upstream: str) -> str:
    global VERSIONS

    if VERSIONS is None:
        # Cache versions
        VERSIONS = _read_versions_file()
    return VERSIONS[upstream]


def _read_versions_file():
    with open(VERSIONS_FILE, mode="r") as versions_file:
        versions = json.loads(versions_file.read())
        return versions


def get_snap_version_data():
    output = run("snap", "list", "microk8s")
    snap_info = output.split("\n")[1]
    version, revision = snap_info.split()[1:3]
    return version, revision


def print_versions() -> None:
    version, revision = get_snap_version_data()
    print(f"MicroK8s {version} revision: {revision}")

    kube_version = get_upstream_version("kube")
    print(f"  - K8s: {kube_version}")

    cni_version = get_upstream_version("cni")
    print(f"  - CNI: {cni_version}")


@click.command(
    context_settings={
        "help_option_names": ["-h", "--help"],
    }
)
def version_command():
    """
    Show version information of MicroK8s and its upstream components.
    """
    print_versions()


if __name__ == "__main__":
    version_command(prog_name="microk8s version")
