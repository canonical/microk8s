#!/usr/bin/python3
import os
import argparse
import subprocess

import requests
import urllib3
from common.utils import exit_if_no_permission, is_cluster_locked

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
CLUSTER_API = "cluster/api/v1.0"
snapdata_path = os.environ.get('SNAP_DATA')
snap_path = os.environ.get('SNAP')


def upgrade_master(upgrade, phase):
    """
    Upgrade the master node
    :param upgrade: which upgrade to call
    :param phase: prepare, commit or rollback
    :return:
    """
    try:
        upgrade_script = '{}/upgrade-scripts/{}/{}-master.sh'.format(snap_path, upgrade, phase)
        if os.path.isfile(upgrade_script):
            print("Running {}-upgrade script".format(phase))
            out = subprocess.check_output(upgrade_script)
            print(out)
    except subprocess.CalledProcessError as e:
        print("{}-upgrade step failed".format(phase))
        raise e


def node_upgrade(upgrade, phase, node_ep, token):
    """
    Upgrade a node
    :param upgrade: which upgrade to call
    :param phase: prepare, commit or rollback
    :param node_ep: the node endpoint the nodes cluster agent listens at
    :param token: the callback token to access the node
    :return:
    """
    try:
        upgrade_script = '{}/upgrade-scripts/{}/{}-node.sh'.format(snap_path, upgrade, phase)
        if os.path.isfile(upgrade_script):
            remote_op = {"callback": token, "phase": phase, "upgrade": upgrade}
            # TODO: handle ssl verification
            res = requests.post(
                "https://{}/{}/upgrade".format(node_ep, CLUSTER_API), json=remote_op, verify=False
            )
            if res.status_code != 200:
                print("Failed to perform a {} on node {}".format(remote_op["upgrade"], node_ep))
                raise Exception("Failed to {} on {}".format(phase, node_ep))
    except subprocess.CalledProcessError as e:
        print("{} upgrade step failed on {}".format(phase, node_ep))
        raise e


def rollback(upgrade):
    """
    The rollback method that oversees the rollback of the cluster
    :param upgrade: which upgrade to call
    """
    # We should get the nodes without checking their existence from the API server
    node_info = get_nodes_info(safe=False)

    upgrade_log_file = "{}/var/log/upgrades/{}.log".format(snapdata_path, upgrade)
    with open(upgrade_log_file, "r") as log:
        for line in log:
            parts = line.split(" ")
            node_type = parts[0]
            phase = parts[1]
            if node_type == "node":
                node_ep = parts[2].rstrip()
            else:
                node_ep = "localhost"
            if phase == "commit":
                print("Rolling back {} on {}".format(phase, node_ep))
                if node_type == "node":
                    tokens = [t for ep, t in node_info if node_ep.startswith(ep)]
                    if len(tokens) != 0:
                        token = tokens[0]
                        node_upgrade(upgrade, "rollback", node_ep, token)
                else:
                    upgrade_master(upgrade, "rollback")


def run_upgrade(upgrade):
    """
    The upgrade method that oversees the upgrade of the cluster
    :param upgrade: which upgrade to call
    """
    node_info = get_nodes_info()

    log_dir = "{}/var/log/upgrades".format(snapdata_path)
    upgrade_log_file = "{}/{}.log".format(log_dir, upgrade)
    try:
        os.makedirs(log_dir, exist_ok=True)
        with open(upgrade_log_file, "w") as log:
            log.writelines(["master prepare"])
            upgrade_master(upgrade, "prepare")
            log.flush()
            for node_ep, token in node_info:
                log.writelines(["\nnode prepare {}".format(node_ep)])
                node_upgrade(upgrade, "prepare", node_ep, token)
                log.flush()

            for node_ep, token in node_info:
                log.writelines(["\nnode commit {}".format(node_ep)])
                node_upgrade(upgrade, "commit", node_ep, token)
                log.flush()

            log.writelines(["\nmaster commit"])
            upgrade_master(upgrade, "commit")
            log.flush()

    except Exception as e:
        print("Error in upgrading. Error: {}".format(e))
        log.close()
        rollback(upgrade)
        exit(2)


def get_nodes_info(safe=True):
    """
    Get the list of node endpoints and tokens in the cluster
    :return:
    """
    callback_tokens_file = "{}/credentials/callback-tokens.txt".format(snapdata_path)
    node_info = []
    if safe:
        try:
            nodes = subprocess.check_output(
                "{}/microk8s-kubectl.wrapper get no".format(snap_path).split()
            )
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
            print("Error in gathering cluster node information. Upgrade aborted.")
            exit(1)
    else:
        if os.path.isfile(callback_tokens_file):
            with open(callback_tokens_file, "r+") as fp:
                for _, line in enumerate(fp):
                    parts = line.split()
                    node_info = [(parts[0], parts[1])]

    return node_info


def list_upgrades():
    """
    List all available upgrades
    """
    upgrades_dir = '{}/upgrade-scripts/'.format(snap_path)
    upgrades = [
        dI for dI in os.listdir(upgrades_dir) if os.path.isdir(os.path.join(upgrades_dir, dI))
    ]
    for u in upgrades:
        print(u)


if __name__ == '__main__':
    exit_if_no_permission()
    is_cluster_locked()

    # initiate the parser with a description
    parser = argparse.ArgumentParser(description='MicroK8s supervised upgrades.', prog='upgrade')
    parser.add_argument(
        "-l", "--list", help="list available upgrades", nargs='?', const=True, type=bool
    )
    parser.add_argument(
        "-r", "--run", help="run a specific upgrade script", nargs='?', type=str, default=None
    )
    parser.add_argument(
        "-u", "--undo", help="rollback a specific upgrade", nargs='?', type=str, default=None
    )
    args = parser.parse_args()

    run = args.run
    ls = args.list
    undo = args.undo

    if ls:
        list_upgrades()
    elif run:
        run_upgrade(run)
    elif undo:
        rollback(undo)
    else:
        print("Unknown option")
        exit(1)

    exit(0)
