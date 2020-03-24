#!/usr/bin/python3
import os
import argparse
import subprocess

import requests
import urllib3
from common.utils import exit_if_no_permission, is_cluster_locked, wait_for_ready, is_cluster_ready, \
    get_available_addons, get_current_arch, get_addon_by_name, kubectl_get, kubectl_get_clusterroles

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
CLUSTER_API = "cluster/api/v1.0"
snapdata_path = os.environ.get('SNAP_DATA')
snap_path = os.environ.get('SNAP')


def pre_upgrade_master(upgrade):
    try:
        pre_upgrade_script='{}/upgrade-scripts/{}/prepare-master.sh'.format(snap_path, upgrade)
        if os.path.isfile(pre_upgrade_script):
            print("Running pre-upgrade script")
            subprocess.check_output(pre_upgrade_script)
    except subprocess.CalledProcessError as e:
        print("Pre-upgrade step failed")
        raise e


def post_upgrade_master(upgrade):
    try:
        upgrade_script='{}/upgrade-scripts/{}/commit-master.sh'.format(snap_path, upgrade)
        if os.path.isfile(upgrade_script):
            print("Running post-upgrade script")
            subprocess.check_output(upgrade_script)
    except subprocess.CalledProcessError as e:
        print("Post-upgrade step failed")
        raise e


def node_upgrade(upgrade, phase, node_ep, token):
    try:
        upgrade_script='{}/upgrade-scripts/{}/commit-node.sh'.format(snap_path, upgrade)
        if os.path.isfile(upgrade_script):
            remote_op = {"callback": token, "phase": phase, "upgrade": upgrade}
            # TODO: handle ssl verification
            res = requests.post("https://{}/{}/upgrade".format(node_ep, CLUSTER_API),
                                json=remote_op,
                                verify=False)
            if res.status_code != 200:
                print("Failed to perform a {} on node {}".format(remote_op["upgrade"], node_ep))
                raise Exception("Failed to {} node {}".format(phase, node_ep))
    except subprocess.CalledProcessError as e:
        print("Post-upgrade step failed")
        raise e


def rollback():
    raise Exception("Rollback not implemented")


def run_upgrade(upgrade):
    callback_tokens_file = "{}/credentials/callback-tokens.txt".format(snapdata_path)
    node_info = []

    try:
        nodes = subprocess.check_output("{}/microk8s-kubectl.wrapper get no".format(snap_path).split())
        if os.path.isfile(callback_tokens_file):
            with open(callback_tokens_file, "r+") as fp:
                for _, line in enumerate(fp):
                    parts = line.split()
                    node_ep = parts[0]
                    host = node_ep.split(":")[0]
                    print("Preparing node {}.".format(host))
                    if host not in nodes.decode():
                        print("Node {} not present".format(host))
                        continue
                    node_info = [(parts[0], parts[1])]
    except subprocess.CalledProcessError:
        print("Error in gathering cluster node information. Upgrade aborting.".format(host))
        exit(1)

    try:
        pre_upgrade_master(upgrade)
        for node_ep, token in node_info:
            node_upgrade(upgrade, "prepare", node_ep, token)

        for node_ep, token in node_info:
            node_upgrade(upgrade, "commit", node_ep, token)

        post_upgrade_master(upgrade)

    except Exception as e:
        print("Error in upgrading. Error: {}".format(e))
        rollback()
        exit(2)


if __name__ == '__main__':
    exit_if_no_permission()
    is_cluster_locked()

    # initiate the parser with a description
    parser = argparse.ArgumentParser(description='Microk8s supervised upgrades.', prog='microk8s.upgrade')
    parser.add_argument("-l", "--list", help="list available upgrades")
    parser.add_argument("-r", "--run", help="run a specific upgrade script", nargs='?', type=str, default=None)
    # read arguments from the command line
    args = parser.parse_args()

    run = args.run
    upgrades_list = args.list

    if upgrades_list:
        print("Not implemented")
        exit(0)

    if run:
        run_upgrade(run)
