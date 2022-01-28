#!/usr/bin/env python3

import os
import subprocess
import yaml


def fetch_addons():
    """Fetch the addons appropriate for this architecture"""
    org = "canonical"
    repo = os.environ["ADDONS_REPO"]
    branch = os.environ["ADDONS_REPO_BRANCH"]
    arch = os.environ["ARCH"]

    cmd = "rm -rf {}".format(org)
    subprocess.check_call(cmd.split())
    cmd = "git clone --depth 1 {} {} -b {}".format(repo, org, branch)
    subprocess.check_call(cmd.split())
    with open("{}/addon-lists.yaml".format(org)) as f:
        info = yaml.safe_load(f)

    for addon in info["microk8s-addons"]["addons"]:
        print("Addon {} is available for {}".format(addon["name"], addon["supported_architectures"]))
        if arch not in addon["supported_architectures"]:
            print("Removing addon {}".format(addon["name"]))
            subprocess.check_call("rm -rf {}/addons/{}".format(org, addon["name"]).split())

    cmd = "rm -rf {}/.git".format(org)
    subprocess.check_call(cmd.split())


if __name__ == '__main__':
    fetch_addons()

