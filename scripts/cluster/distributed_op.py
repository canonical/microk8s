#!/usr/bin/python3
import getopt
import subprocess

import requests
import urllib3
import os
import sys
import json
import socket

from common.utils import is_node_running_dqlite

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
CLUSTER_API = "cluster/api/v1.0"
snapdata_path = os.environ.get('SNAP_DATA')
snap_path = os.environ.get('SNAP')
callback_tokens_file = "{}/credentials/callback-tokens.txt".format(snapdata_path)
callback_token_file = "{}/credentials/callback-token.txt".format(snapdata_path)


def do_op(remote_op):
    """
    Perform an operation on a remote node
    
    :param remote_op: the operation json string
    """
    if is_node_running_dqlite():
        try:
            hostname = socket.gethostname()
            with open(callback_token_file, "r+") as fp:
                token = fp.read()

            subprocess.check_output(
                "{}/microk8s-status.wrapper --wait-ready --timeout=60".format(snap_path).split()
            )
            nodes_info = subprocess.check_output(
                "{}/microk8s-kubectl.wrapper get no -o json".format(snap_path).split()
            )
            info = json.loads(nodes_info.decode())
            for node_info in info["items"]:
                node = node_info['metadata']['name']
                # TODO: What if the user has set a hostname override in the kubelet args?
                if node == hostname:
                    continue
                print("Configuring node {}".format(node))
                # TODO: make port configurable
                node_ep = "{}:{}".format(node, '25000')
                remote_op["callback"] = token.rstrip()
                # TODO: handle ssl verification
                res = requests.post(
                    "https://{}/{}/configure".format(node_ep, CLUSTER_API),
                    json=remote_op,
                    verify=False,
                )
                if res.status_code != 200:
                    print(
                        "Failed to perform a {} on node {} {}".format(
                            remote_op["action_str"], node_ep, res.status_code
                        )
                    )
        except subprocess.CalledProcessError:
            print("Could not query for nodes")

    else:
        with open(callback_tokens_file, "r+") as fp:
            for _, line in enumerate(fp):
                parts = line.split()
                node_ep = parts[0]
                host = node_ep.split(":")[0]
                print("Applying to node {}.".format(host))
                try:
                    # Make sure this node exists
                    subprocess.check_call(
                        "{}/microk8s-kubectl.wrapper get no {}".format(snap_path, host).split(),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    token = parts[1]
                    remote_op["callback"] = token
                    # TODO: handle ssl verification
                    res = requests.post(
                        "https://{}/{}/configure".format(node_ep, CLUSTER_API),
                        json=remote_op,
                        verify=False,
                    )
                    if res.status_code != 200:
                        print(
                            "Failed to perform a {} on node {}".format(
                                remote_op["action_str"], node_ep
                            )
                        )
                except subprocess.CalledProcessError:
                    print("Node {} not present".format(host))


def restart(service):
    """
    Restart service on all nodes
    
    :param service: the service name
    """
    print("Restarting nodes.")
    remote_op = {
        "action_str": "restart {}".format(service),
        "service": [{"name": service, "restart": "yes"}],
    }
    do_op(remote_op)


def update_argument(service, key, value):
    """
    Configure an argument on all nodes

    :param service: the service we configure
    :param key: the argument we configure
    :param value: the value we set
    """
    print("Adding argument {} to nodes.".format(key))
    remote_op = {
        "action_str": "change of argument {} to {}".format(key, value),
        "service": [{"name": service, "arguments_update": [{key: value}]}],
    }
    do_op(remote_op)


def remove_argument(service, key):
    """
    Drop an argument from all nodes

    :param service: the service we configure
    :param key: the argument we configure
    """
    print("Removing argument {} from nodes.".format(key))
    remote_op = {
        "action_str": "removal of argument {}".format(key),
        "service": [{"name": service, "arguments_remove": [key]}],
    }
    do_op(remote_op)


def set_addon(addon, state):
    """
    Enable or disable an add-on across all nodes

    :param addon: the add-on name
    :param state: 'enable' or 'disable'
    """
    if state not in ("enable", "disable"):
        raise ValueError(
            "Wrong value '{}' for state. Must be one of 'enable' or 'disable'".format(state)
        )
    else:
        print("Setting add-on {} to {} on nodes.".format(addon, state))
        remote_op = {
            "action_str": "set of {} to {}".format(addon, state),
            "addon": [{"name": addon, state: "true"}],
        }
        do_op(remote_op)


def usage():
    print("usage: dist_refresh_opt [OPERATION] [SERVICE] (ARGUMENT) (value)")
    print("OPERATION is one of restart, update_argument, remove_argument, set_addon")


if __name__ == "__main__":
    if is_node_running_dqlite() and not os.path.isfile(callback_token_file):
        # print("Single node cluster.")
        exit(0)

    if not is_node_running_dqlite() and not os.path.isfile(callback_tokens_file):
        print("No callback tokens file.")
        exit(1)

    try:
        opts, args = getopt.getopt(sys.argv[1:], "h", ["help"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    operation = args[0]
    service = args[1]
    if operation == "restart":
        restart(service)
    if operation == "update_argument":
        update_argument(service, args[2], args[3])
    if operation == "remove_argument":
        remove_argument(service, args[2])
    if operation == "set_addon":
        set_addon(service, args[2])
    exit(0)
