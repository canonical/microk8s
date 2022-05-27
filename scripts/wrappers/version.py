#!/usr/bin/env python3

import json
from os import environ, getenv
from pathlib import Path


def get_upstream_versions() -> str:
    versions_file = Path(environ["SNAP"]) / "versions.json"
    with open(versions_file, mode="r") as file:
        versions = json.loads(file.read())
        return versions


def get_snap_version() -> str:
    return getenv("SNAP_VERSION", "(unknown)")


def get_snap_revision() -> str:
    return getenv("SNAP_REVISION", "(unknown)")


def print_versions() -> None:
    version = get_snap_version()
    revision = get_snap_revision()
    print(f"MicroK8s {version} revision: {revision}")

    upstream_versions = get_upstream_versions()
    kube_version = upstream_versions["kube"]
    print(f"  - K8s: {kube_version}")


if __name__ == "__main__":
    print_versions()
