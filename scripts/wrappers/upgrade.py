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


def upgrade_master(upgrade, phase):
    try:
        upgrade_script='{}/upgrade-scripts/{}/{}-master.sh'.format(snap_path, upgrade, phase)
        if os.path.isfile(upgrade_script):
            print("Running {}-upgrade script".format(phase))
            subprocess.check_output(upgrade_script)
    except subprocess.CalledProcessError as e:
        print("{}-upgrade step failed".format(phase))
        raise e


def node_upgrade(upgrade, phase, node_ep, token):
    try:
        upgrade_script='{}/upgrade-scripts/{}/{}-node.sh'.format(snap_path, upgrade, phase)
        if os.path.isfile(upgrade_script):
            remote_op = {"callback": token, "phase": phase, "upgrade": upgrade}
            # TODO: handle ssl verification
            res = requests.post("https://{}/{}/upgrade".format(node_ep, CLUSTER_API),
                                json=remote_op,
                                verify=False)
            if res.status_code != 200:
                print("Failed to perform a {} on node {}".format(remote_op["upgrade"], node_ep))
                raise Exception("Failed to {} on {}".format(phase, node_ep))
    except subprocess.CalledProcessError as e:
        print("{} upgrade step failed on {}".format(phase, node_ep))
        raise e


def rollback(upgrade):
    node_info = get_nodes_info()

    upgrade_log_file = "{}/var/log/upgrades/{}.log".format(upgrade)
    with open(upgrade_log_file, "r") as log:
        line = log.readline()
        parts = line.split(" ")
        node_type = parts[0]
        phase = parts[1]
        if node_type == "node":
            node_ep = parts[2]
        else:
            node_ep = "localhost"
        if phase == "commit":
            print("Rolling back {} on {}".format(phase, node_ep))
            if node_type == "node":
                tokens = [t for ep, t in node_info if node_ep == ep]
                if len(tokens != 0):
                    token = tokens[0]
                    node_upgrade(upgrade, "rollback", node_ep, token)
            else:
                upgrade_master(upgrade, "rollback")


def run_upgrade(upgrade):
    node_info = get_nodes_info()

    upgrade_log_file = "{}/var/log/upgrades/{}.log".format(upgrade)
    try:
        with open(upgrade_log_file, "w") as log:
            upgrade_master(upgrade, "prepare")
            log.writelines(["master prepare"])
            log.flush()
            for node_ep, token in node_info:
                node_upgrade(upgrade, "prepare", node_ep, token)
                log.writelines(["node prepare {}".format(node_ep)])
                log.flush()

            for node_ep, token in node_info:
                node_upgrade(upgrade, "commit", node_ep, token)
                log.writelines(["node commit {}".format(node_ep)])
                log.flush()

            upgrade_master(upgrade, "commit")
            log.writelines(["master commit"])
            log.flush()

    except Exception as e:
        print("Error in upgrading. Error: {}".format(e))
        log.close()
        rollback(upgrade_log_file)
        exit(2)


def get_nodes_info():
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
                    if host not in nodes.decode():
                        print("Node {} not present".format(host))
                        continue
                    node_info = [(parts[0], parts[1])]
    except subprocess.CalledProcessError:
        print("Error in gathering cluster node information. Upgrade aborted.".format(host))
        exit(1)
    return node_info


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
