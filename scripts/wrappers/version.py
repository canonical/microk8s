#!/usr/bin/env python3

from os import getenv


def get_snap_version() -> str:
    return getenv("SNAP_VERSION", "(unknown)")


def get_snap_revision() -> str:
    return getenv("SNAP_REVISION", "(unknown)")


def print_versions() -> None:
    version = get_snap_version()
    revision = get_snap_revision()
    print(f"MicroK8s {version} revision {revision}")


if __name__ == "__main__":
    print_versions()
