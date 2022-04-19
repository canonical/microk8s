#!/usr/bin/env python3

import click
import json
from os import environ
from pathlib import Path


def get_upstream_versions() -> str:
    versions_file = Path(environ["SNAP"]) / "versions.json"
    with open(versions_file, mode="r") as file:
        versions = json.loads(file.read())
        return versions


def get_snap_version() -> str:
    return environ["SNAP_VERSION"]


def get_snap_revision() -> str:
    return environ["SNAP_REVISION"]


def print_versions() -> None:
    version = get_snap_version()
    revision = get_snap_revision()
    print(f"MicroK8s {version} revision: {revision}")

    upstream_versions = get_upstream_versions()
    kube_version = upstream_versions["kube"]
    cni_version = upstream_versions["cni"]
    print(f"  - K8s: {kube_version}")
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
