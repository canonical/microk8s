#!/usr/bin/python3
import json
import os
import shutil
import subprocess
import sys

import click
import netifaces

from ipaddress import ip_address

from common.cluster.utils import (
    try_set_file_permissions,
    is_node_running_dqlite,
    is_token_auth_enabled,
)

snap_path = os.environ.get("SNAP")
snapdata_path = os.environ.get("SNAP_DATA")
callback_tokens_file = "{}/credentials/callback-tokens.txt".format(snapdata_path)

cluster_dir = "{}/var/kubernetes/backend".format(snapdata_path)


def remove_dqlite_node(node, force=False):
    try:
        # If node is an IP address, find the node name.
        is_node_ip = True
        try:
            ip_address(node)
        except ValueError:
            is_node_ip = False

        if is_node_ip:
            node_info = subprocess.check_output(
                "{}/microk8s-kubectl.wrapper get no -o json".format(snap_path).split()
            )
            info = json.loads(node_info.decode())
            found = False
            for n in info["items"]:
                if found:
                    break
                for a in n["status"]["addresses"]:
                    if a["type"] == "InternalIP" and a["address"] == node:
                        node = n["metadata"]["name"]
                        found = True
                        break

        # Make sure this node exists
        node_info = subprocess.check_output(
            "{}/microk8s-kubectl.wrapper get no {} -o json".format(snap_path, node).split()
        )
        info = json.loads(node_info.decode())
        node_address = None
        for a in info["status"]["addresses"]:
            if a["type"] == "InternalIP":
                node_address = a["address"]
                break

        if not node_address:
            print("Node {} is not part of the cluster.".format(node))
            exit(1)

        node_ep = None
        my_ep, other_ep = get_dqlite_endpoints()
        for ep in other_ep:
            if ep.startswith("{}:".format(node_address)):
                node_ep = ep

        if node_ep and force:
            delete_dqlite_node([node_ep], my_ep)
        elif node_ep and not force:
            print(
                "Removal failed. Node {} is registered with dqlite. "
                "Please, run first 'microk8s leave' on the departing node. \n"
                "If the node is not available anymore and will never attempt to join the cluster "
                "in the future use the '--force' flag \n"
                "to unregister the node while removing it.".format(node)
            )
            exit(1)

    except subprocess.CalledProcessError:
        print("Node {} does not exist in Kubernetes.".format(node))
        if force:
            print("Attempting to remove {} from dqlite.".format(node))
            # Make sure we do not have the node in dqlite.
            # We assume the IP is provided to denote the
            my_ep, other_ep = get_dqlite_endpoints()
            for ep in other_ep:
                if ep.startswith("{}:".format(node)):
                    print("Removing node entry found in dqlite.")
                    delete_dqlite_node([ep], my_ep)
        exit(1)

    remove_node(node)


def remove_node(node):
    try:
        # Make sure this node exists
        subprocess.check_call(
            "{}/microk8s-kubectl.wrapper get no {}".format(snap_path, node).split(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        print("Node {} does not exist.".format(node))
        exit(1)

    if is_token_auth_enabled():
        remove_kubelet_token(node)
    remove_callback_token(node)
    subprocess.check_call(
        "{}/microk8s-kubectl.wrapper delete no {}".format(snap_path, node).split(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def remove_kubelet_token(node):
    """
    Remove a token for a node in the known tokens

    :param node: the name of the node
    """
    file = "{}/credentials/known_tokens.csv".format(snapdata_path)
    backup_file = "{}.backup".format(file)
    token = "system:node:{}".format(node)
    # That is a critical section. We need to protect it.
    with open(backup_file, "w") as back_fp:
        with open(file, "r") as fp:
            for _, line in enumerate(fp):
                if token in line:
                    continue
                back_fp.write("{}".format(line))

    try_set_file_permissions(backup_file)
    shutil.copyfile(backup_file, file)


def get_dqlite_endpoints():
    """
    Return the endpoints the current node has on dqlite and the endpoints of the rest of the nodes.

    :return: two lists with the endpoints
    """
    out = subprocess.check_output(
        "{snappath}/bin/dqlite -s file://{dbdir}/cluster.yaml -c {dbdir}/cluster.crt "
        "-k {dbdir}/cluster.key -f json k8s .cluster".format(
            snappath=snap_path, dbdir=cluster_dir
        ).split()
    )
    data = json.loads(out.decode())
    ep_addresses = []
    for ep in data:
        ep_addresses.append(ep["Address"])
    local_ips = []
    for interface in netifaces.interfaces():
        if netifaces.AF_INET not in netifaces.ifaddresses(interface):
            continue
        for link in netifaces.ifaddresses(interface)[netifaces.AF_INET]:
            local_ips.append(link["addr"])
    my_ep = []
    other_ep = []
    for ep in ep_addresses:
        found = False
        for ip in local_ips:
            if "{}:".format(ip) in ep:
                my_ep.append(ep)
                found = True
        if not found:
            other_ep.append(ep)

    return my_ep, other_ep


def delete_dqlite_node(delete_node, dqlite_ep):
    if len(delete_node) > 0 and "127.0.0.1" not in delete_node[0]:
        for ep in dqlite_ep:
            try:
                cmd = (
                    "{snappath}/bin/dqlite -s file://{dbdir}/cluster.yaml -c {dbdir}/cluster.crt "
                    "-k {dbdir}/cluster.key -f json k8s".format(
                        snappath=snap_path, dbdir=cluster_dir
                    ).split()
                )
                cmd.append(".remove {}".format(delete_node[0]))
                subprocess.check_output(cmd)
                break
            except Exception as err:
                print("Contacting node {} failed. Error:".format(ep))
                print(repr(err))
                exit(2)


def remove_callback_token(node):
    """
    Remove a callback token

    :param node: the node
    """
    tmp_file = "{}.tmp".format(callback_tokens_file)
    if not os.path.isfile(callback_tokens_file):
        open(callback_tokens_file, "a+")
        os.chmod(callback_tokens_file, 0o600)
    with open(tmp_file, "w") as backup_fp:
        os.chmod(tmp_file, 0o600)
        with open(callback_tokens_file, "r+") as callback_fp:
            # Entries are of the format: 'node_hostname:agent_port token'
            # We need to get the node_hostname part
            for line in callback_fp:
                parts = line.split(":")
                if parts[0] == node:
                    continue
                else:
                    backup_fp.write(line)

    try_set_file_permissions(tmp_file)
    shutil.move(tmp_file, callback_tokens_file)


@click.command()
@click.argument("node", required=True)
@click.option(
    "--force",
    is_flag=True,
    required=False,
    default=False,
    help="Force the node removal operation. (default: false)",
)
def reset(node, force):
    """
    Remove a node from the cluster
    """
    if is_node_running_dqlite():
        remove_dqlite_node(node, force)
    else:
        remove_node(node)
    sys.exit(0)


if __name__ == "__main__":
    reset(prog_name="microk8s remove-node")
