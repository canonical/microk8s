#!/usr/bin/env python3

import os
import click
import subprocess
import yaml


@click.command()
@click.option(
    "--addons-only",
    is_flag=True,
    required=False,
    default=False,
    help="Remove non-essential files, eg tests, README, etc",
)
@click.option(
    "--target-directory",
    required=False,
    default="core",
    help="The output directory (relative to the current path) we want the addons to be placed in. WARNING: a pre-existing directory will be removed",
)
def fetch_addons(addons_only, target_directory):
    """Fetch the addons appropriate for this architecture"""
    repo = os.environ["ADDONS_REPO"]
    branch = os.environ["ADDONS_REPO_BRANCH"]
    arch = os.environ["ARCH"]

    cmd = "rm -rf {}".format(target_directory)
    subprocess.check_call(cmd.split())
    cmd = "git clone --depth 1 {} {} -b {}".format(repo, target_directory, branch)
    subprocess.check_call(cmd.split())
    with open("{}/addons.yaml".format(target_directory)) as f:
        info = yaml.safe_load(f)

    for addon in info["microk8s-addons"]["addons"]:
        print(
            "Addon {} is available for {}".format(addon["name"], addon["supported_architectures"])
        )
        if arch not in addon["supported_architectures"]:
            print("Removing addon {}".format(addon["name"]))
            subprocess.check_call(
                "rm -rf {}/addons/{}".format(target_directory, addon["name"]).split()
            )

    if addons_only:
        cmd = "rm -rf {0}/.git {0}/.gitignore {0}/tests {0}/README.md {0}/LICENSE".format(
            target_directory
        )
        subprocess.check_call(cmd.split())


if __name__ == "__main__":
    fetch_addons()
