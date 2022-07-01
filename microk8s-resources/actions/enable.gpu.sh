#!/usr/bin/env python3

import json
import os
import pathlib
import subprocess
import time

import click


DIR = pathlib.Path(__file__).absolute().parent
SNAP = pathlib.Path(os.getenv("SNAP") or "/snap/microk8s/current")
SNAP_DATA = pathlib.Path(os.getenv("SNAP_DATA") or "/var/snap/microk8s/current")
SNAP_CURRENT = SNAP_DATA.parent / "current"
SNAP_COMMON = pathlib.Path(os.getenv("SNAP_COMMON") or "/var/snap/microk8s/common")

HELM = SNAP / "microk8s-helm3.wrapper"
MICROK8S_ENABLE = SNAP / "microk8s-enable.wrapper"
CONTAINERD_SOCKET = SNAP_COMMON / "run" / "containerd.sock"
CONTAINERD_TOML = SNAP_CURRENT / "args" / "containerd-template.toml"


def log(msg):
    click.echo(msg, err=True)


@click.command()
@click.argument(
    "driver-type",
    default="",
    type=click.Choice(["", "force-operator-driver", "force-system-driver"]),
)
@click.option("--requires", multiple=True, default=["core/dns", "core/helm3"])
@click.option("--version", default="v1.11.0")
@click.option("--driver", default="auto", type=click.Choice(["auto", "operator", "host"]))
@click.option("--toolkit-version", default=None)
@click.option("--set-as-default-runtime/--no-set-as-default-runtime", is_flag=True, default=True)
@click.option("--set", "helm_set", multiple=True)
@click.option("-f", "--values", "helm_values", multiple=True, type=click.Path(exists=True))
def main(
    requires: list,
    version: str,
    driver_type: str,
    driver: str,
    toolkit_version: str,
    set_as_default_runtime: bool,
    helm_set: list,
    helm_values: list,
):
    click.echo("Enabling NVIDIA GPU")

    for addon in requires:
        subprocess.run([MICROK8S_ENABLE, addon])

    # handle the deprecated force-operator-driver and force-system-driver options
    if driver_type == "force-operator-driver":
        driver = "operator"
        click.echo(f"WARNING: {driver_type} is deprecated. Please use --driver=operator")
    elif driver_type == "force-system-driver":
        driver = "host"
        click.echo(f"WARNING: {driver_type} is deprecated. Please use --driver=host")
    elif driver == "auto":
        try:
            click.echo("Checking if NVIDIA driver is already installed")
            subprocess.check_call(["nvidia-smi", "-L"])
            driver = "host"
        except OSError:
            driver = "operator"

    click.echo(f"Using {driver} GPU driver")
    helm_args = [
        "install",
        "gpu-operator",
        "nvidia/gpu-operator",
        f"--version={version}",
        "--create-namespace",
        "--namespace=gpu-operator-resources",
        "-f",
        "-",
    ]

    helm_config = {
        "operator": {
            "defaultRuntime": "containerd",
        },
        "driver": {
            "enabled": ("true" if driver == "operator" else "false"),
        },
        "toolkit": {
            "enabled": "true",
            "env": [
                {"name": "CONTAINERD_CONFIG", "value": CONTAINERD_TOML.as_posix()},
                {"name": "CONTAINERD_SOCKET", "value": CONTAINERD_SOCKET.as_posix()},
                {
                    "name": "CONTAINERD_SET_AS_DEFAULT",
                    "value": "1" if set_as_default_runtime else "0",
                },
            ],
        },
    }
    if toolkit_version is not None:
        helm_config["toolkit"]["version"] = toolkit_version

    for arg in helm_set:
        helm_args.extend(["--set", arg])
    for arg in helm_values:
        helm_args.extend(["--values", arg])

    subprocess.run([HELM, "repo", "add", "nvidia", "https://nvidia.github.io/gpu-operator"])
    subprocess.run([HELM, *helm_args], input=json.dumps(helm_config).encode())

    click.echo("NVIDIA is enabled")


if __name__ == "__main__":
    main()
