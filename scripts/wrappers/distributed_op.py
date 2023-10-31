#!/usr/bin/python3
import getopt
import subprocess

import requests
import urllib3
import os
import sys
import json
import socket
import time

from common.cluster.utils import (
    get_callback_token,
    get_cluster_agent_port,
    is_node_running_dqlite,
    get_internal_ip_from_get_node,
    is_same_server,
)


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
CLUSTER_API_V1 = "cluster/api/v1.0"
CLUSTER_API_V2 = "cluster/api/v2.0"
snapdata_path = os.environ.get("SNAP_DATA")
snap_path = os.environ.get("SNAP")
callback_tokens_file = "{}/credentials/callback-tokens.txt".format(snapdata_path)
callback_token_file = "{}/credentials/callback-token.txt".format(snapdata_path)

KUBECTL = "{}/microk8s-kubectl.wrapper".format(snap_path)
MICROK8S_STATUS = "{}/microk8s-status.wrapper".format(snap_path)


def get_cluster_agent_endpoints(include_self=False):
    """
    Get a list of all cluster agent endpoints and their callback token.

    :param include_self: If true, include the current node in the list.

    :return: [("node1:25000", "token1"), ("node2:25000", "token2"), ...]
    """
    nodes = []
    if is_node_running_dqlite():
        hostname = socket.gethostname()
        token = get_callback_token()

        for attempt in range(10):
            try:
                stdout = subprocess.check_output([KUBECTL, "get", "node", "-o", "json"])
                break
            except subprocess.CalledProcessError as e:
                print("Failed to list nodes (try {}): {}".format(attempt + 1, e), file=sys.stderr)
                if attempt == 9:
                    raise e
                time.sleep(3)

        info = json.loads(stdout)
        for node_info in info["items"]:
            node_ip = get_internal_ip_from_get_node(node_info)
            if not include_self and is_same_server(hostname, node_ip):
                continue

            nodes.append(("{}:25000".format(node_ip), token.rstrip()))
    else:
        if include_self:
            token = get_callback_token()
            port = get_cluster_agent_port()
            nodes.append(("127.0.0.1:{}".format(port), token.rstrip()))

        try:
            with open(callback_tokens_file, "r+") as fin:
                for line in fin:
                    node_ep, token = line.split()
                    host = node_ep.split(":")[0]

                    try:
                        subprocess.check_call(
                            [KUBECTL, "get", "node", host],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        nodes.append((node_ep, token.rstrip()))
                    except subprocess.CalledProcessError:
                        print("Node {} not present".format(host))
        except OSError:
            pass
    return nodes


def do_configure_op(remote_op):
    """
    Perform a /configure operation on all remote nodes

    :param remote_op: the operation json string
    """
    try:
        endpoints = get_cluster_agent_endpoints(include_self=False)
    except subprocess.CalledProcessError as e:
        print("Could not query for nodes")
        raise SystemExit(e)

    for node_ep, token in endpoints:
        try:
            remote_op["callback"] = token.rstrip()
            # TODO: handle ssl verification
            res = requests.post(
                "https://{}/{}/configure".format(node_ep, CLUSTER_API_V1),
                json=remote_op,
                verify=False,
            )
            if res.status_code != 200:
                print(
                    "Failed to perform a {} on node {} {}".format(
                        remote_op["action_str"], node_ep, res.status_code
                    )
                )
        except requests.exceptions.RequestException as e:
            print("Failed to reach node.")
            raise SystemExit(e)


def do_image_import(image_data):
    """
    Perform a /image/import operation on all nodes

    :param image_data: Raw bytes of the OCI image tar file
    """

    try:
        endpoints = get_cluster_agent_endpoints(include_self=True)
    except subprocess.CalledProcessError as e:
        print("Could not query for nodes")
        raise SystemExit(e)

    for node_ep, token in endpoints:
        try:
            print("Pushing OCI images to {}".format(node_ep))
            res = requests.post(
                "https://{}/{}/image/import".format(node_ep, CLUSTER_API_V2),
                data=image_data,
                headers={
                    "x-microk8s-callback-token": token,
                },
                verify=False,
            )

            if res.status_code != 200:
                print("Failed to import images on {}: {}".format(node_ep, res.content.decode()))
        except requests.exceptions.RequestException as e:
            print("Failed to reach {}: {}".format(node_ep, e))


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
    do_configure_op(remote_op)


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
    do_configure_op(remote_op)


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
    do_configure_op(remote_op)


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
        do_configure_op(remote_op)


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
