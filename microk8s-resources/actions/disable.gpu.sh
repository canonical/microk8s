#!/usr/bin/env python3

import os
import json
import pathlib
import subprocess

import click

SNAP = pathlib.Path(os.getenv("SNAP") or "/snap/microk8s/current")
HELM = SNAP / "microk8s-helm3.wrapper"


@click.command()
def main():
    click.echo("Disabling NVIDIA GPU support")
    try:
        stdout = subprocess.check_output([HELM, "ls", "-A", "-o", "json"])
        charts = json.loads(stdout)
    except (OSError, json.JSONDecodeError):
        click.echo("ERROR: Failed to retrieve installed charts", err=True)
        charts = []

    for chart in charts:
        name = chart.get("name")
        if chart.get("name") == "gpu-operator":
            namespace = chart.get("namespace") or "default"
            subprocess.run([HELM, "uninstall", name, "-n", namespace])

    click.echo("GPU support disabled")


if __name__ == "__main__":
    main()
