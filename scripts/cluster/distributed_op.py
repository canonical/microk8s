#!/usr/bin/python3
import getopt
import subprocess
from typing import Tuple, List, Optional

import yaml

import requests
import urllib3  # type: ignore
import os
import sys
import socket


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
CLUSTER_API = "cluster/api/v1.0"  # type: str
snapdata_path = os.environ.get('SNAP_DATA')  # type: Optional[str]
snap_path = os.environ.get('SNAP')  # type: Optional[str]
callback_token_file = "{}/credentials/callback-token.txt".format(snapdata_path)  # type: str


def do_op(remote_op) -> None:
    """
    Perform an operation on a remote node
    
    :param remote_op: the operation json string
    """
    with open(callback_token_file, "r+") as fp:
        token = fp.read()  # type: str
        hostname = socket.gethostname()  # type: str
        try:
            # Make sure this node exists
            subprocess.check_output("{}/microk8s-status.wrapper --wait-ready --timeout=60".format(snap_path).split())
            node_yaml = subprocess.check_output("{}/microk8s-kubectl.wrapper get no -o yaml".format(snap_path).split())
            nodes_info = yaml.load(node_yaml, Loader=yaml.FullLoader)
            for node_info in nodes_info["items"]:
                node = node_info['metadata']['name']  # type: str
                # TODO: What if the user has set a hostname override in the kubelet args?
                if node == hostname:
                    continue
                print("Configuring node {}".format(node))
                # TODO: make port configurable
                node_ep = "{}:{}".format(node, '25000')  # type: str
                remote_op["callback"] = token.rstrip()
                # TODO: handle ssl verification
                res = requests.post("https://{}/{}/configure".format(node_ep, CLUSTER_API),
                                                                json=remote_op,
                                                                verify=False)  # type: requests.models.Response
                if res.status_code != 200:
                    print("Failed to perform a {} on node {} {}".format(remote_op["action_str"],
                                                                        node_ep,
                                                                        res.status_code))
        except subprocess.CalledProcessError:
            print("Node not present")


def restart(service: str) -> None:
    """
    Restart service on all nodes
    
    :param service: the service name
    """
    print("Restarting nodes.")
    remote_op = {
        "action_str": "restart {}".format(service),
        "service": [
            {
                "name": service,
                "restart": "yes"
            }
        ]
    }
    do_op(remote_op)


def update_argument(service: str, key: str, value: str) -> None:
    """
    Configure an argument on all nodes

    :param service: the service we configure
    :param key: the argument we configure
    :param value: the value we set
    """
    print("Adding argument {} to nodes.".format(key))
    remote_op = {
        "action_str": "change of argument {} to {}".format(key, value),
        "service": [
            {
                "name": service,
                "arguments_update": [
                    {key: value}
                ]
            }
        ]
    }
    do_op(remote_op)


def remove_argument(service: str, key: str):
    """
    Drop an argument from all nodes

    :param service: the service we configure
    :param key: the argument we configure
    """
    print("Removing argument {} from nodes.".format(key))
    remote_op = {
        "action_str": "removal of argument {}".format(key),
        "service": [
            {
                "name": service,
                "arguments_remove": [key]
            }
        ]
    }
    do_op(remote_op)


def set_addon(addon: str, state: str) -> None:
    """
    Enable or disable an add-on across all nodes

    :param addon: the add-on name
    :param state: 'enable' or 'disable'
    """
    if state not in ("enable","disable"):
        raise ValueError("Wrong value '{}' for state. Must be one of 'enable' or 'disable'".format(state))
    else:
        print("Setting add-on {} to {} on nodes.".format(addon, state))
        remote_op = {
            "action_str": "set of {} to {}".format(addon, state),
            "addon": [
                {
                    "name": addon,
                    state: "true"
                }
            ]
        }
        do_op(remote_op)


def usage() -> None:
    print("usage: dist_refresh_opt [OPERATION] [SERVICE] (ARGUMENT) (value)")
    print("OPERATION is one of restart, update_argument, remove_argument, set_addon")


if __name__ == "__main__":
    if not os.path.isfile(callback_token_file):
        print("No callback tokens file.")
        exit(1)

    try:
        # params: Tuple[List[Tuple[str, str]], List[str]]
        params = getopt.getopt(sys.argv[1:], "h", ["help"])
        opts = params[0]  # type: List[Tuple[str, str]]
        args = params[1]  # type: List[str]
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

    operation = args[0]  # type: str
    service = args[1]  # type: str
    if operation == "restart":
        restart(service)
    if operation == "update_argument":
        update_argument(service, args[2], args[3])
    if operation == "remove_argument":
        remove_argument(service, args[2])
    if operation == "set_addon":
        set_addon(service, args[2])
    exit(0)
