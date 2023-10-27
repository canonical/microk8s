#!/usr/bin/python3
import json
import os
import shutil
import socket
import subprocess
import sys
import time

import click
import netifaces
import yaml

from common.cluster.utils import (
    is_node_running_dqlite,
    service,
    unmark_no_cert_reissue,
    restart_all_services,
    is_node_dqlite_worker,
    rebuild_x509_auth_client_configs,
)

snapdata_path = os.environ.get("SNAP_DATA")
snap_path = os.environ.get("SNAP")
ca_cert_file = "{}/certs/ca.remote.crt".format(snapdata_path)
callback_token_file = "{}/credentials/callback-token.txt".format(snapdata_path)
server_cert_file = "{}/certs/server.remote.crt".format(snapdata_path)

cluster_dir = "{}/var/kubernetes/backend".format(snapdata_path)
cluster_backup_dir = "{}/var/kubernetes/backend.backup".format(snapdata_path)


def reset_current_dqlite_worker_installation():
    """
    Take a node out of a cluster
    """
    print("Configuring services.", flush=True)
    disable_apiserver_proxy()
    os.remove(ca_cert_file)

    service("stop", "apiserver")
    service("stop", "k8s-dqlite")
    rebuild_x509_auth_client_configs()

    print("Generating new cluster certificates.", flush=True)
    reinit_cluster()

    for config_file in ["kubelet", "kube-proxy"]:
        shutil.copyfile(
            "{}/default-args/{}".format(snap_path, config_file),
            "{}/args/{}".format(snapdata_path, config_file),
        )

    unmark_no_cert_reissue()
    unmark_worker_node()
    restart_all_services()
    apply_cni()


def disable_apiserver_proxy():
    """
    Stop apiserver-proxy
    """
    lock_path = os.path.expandvars("${SNAP_DATA}/var/lock")
    lock = "{}/no-apiserver-proxy".format(lock_path)
    if not os.path.exists(lock):
        open(lock, "a").close()
    service("stop", "apiserver-proxy")


def unmark_worker_node():
    """
    Unmark a node as being part of a cluster not running the control plane
    by deleting a var/lock/clustered.lock
    """
    locks = ["clustered.lock", "no-k8s-dqlite"]
    for lock in locks:
        lock_file = "{}/var/lock/{}".format(snapdata_path, lock)
        if not os.path.isfile(lock_file):
            print("Not in clustering mode.")
            exit(2)
        os.remove(lock_file)


def reset_current_etcd_installation():
    """
    Take a node out of a cluster
    """
    lock_file = "{}/var/lock/clustered.lock".format(snapdata_path)
    if not os.path.isfile(lock_file):
        print("Not in clustering mode.")
        exit(2)

    os.remove(lock_file)
    os.remove(ca_cert_file)
    os.remove(callback_token_file)
    os.remove(server_cert_file)

    for config_file in ["kubelet", "flanneld", "kube-proxy"]:
        shutil.copyfile(
            "{}/default-args/{}".format(snap_path, config_file),
            "{}/args/{}".format(snapdata_path, config_file),
        )

    for user in ["proxy", "kubelet"]:
        config = "{}/credentials/{}.config".format(snapdata_path, user)
        shutil.copyfile("{}.backup".format(config), config)

    subprocess.check_call("{}/microk8s-stop.wrapper".format(snap_path).split())
    waits = 10
    while waits > 0:
        try:
            subprocess.check_call("{}/microk8s-start.wrapper".format(snap_path).split())
            break
        except subprocess.CalledProcessError:
            print("Services not ready to start. Waiting...")
            time.sleep(5)
            waits -= 1

    unmark_no_cert_reissue()


def reset_current_dqlite_installation():
    """
    Take a node out of a dqlite cluster
    """
    if is_leader_without_successor():
        print(
            "This node currently holds the only copy of the Kubernetes "
            "database so it cannot leave the cluster."
        )
        print(
            "To remove this node you can either first remove all other "
            "nodes with 'microk8s remove-node' or"
        )
        print("form a highly available cluster by adding at least three nodes.")
        exit(3)

    # We need to:
    # 1. Stop the apiserver
    # 2. Send a DELETE request to any member of the dqlite cluster
    # 3. wipe out the existing installation
    my_ep, other_ep = get_dqlite_endpoints()

    service("stop", "apiserver")
    service("stop", "k8s-dqlite")
    time.sleep(10)

    delete_dqlite_node(my_ep, other_ep)

    print("Generating new cluster certificates.", flush=True)
    reinit_cluster()
    rebuild_x509_auth_client_configs()

    service("start", "k8s-dqlite")
    service("start", "apiserver")

    apply_cni()
    unmark_no_cert_reissue()
    restart_all_services()


def apply_cni():
    waits = 10  # type: int
    print("Waiting for node to start.", end=" ", flush=True)
    time.sleep(10)
    while waits > 0:
        try:
            subprocess.check_call(
                "{}/microk8s-kubectl.wrapper get service/kubernetes".format(snap_path).split(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.check_call(
                "{}/microk8s-kubectl.wrapper apply -f {}/args/cni-network/cni.yaml".format(
                    snap_path, snapdata_path
                ).split(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            break
        except subprocess.CalledProcessError:
            print(".", end=" ", flush=True)
            time.sleep(5)
            waits -= 1
    print(" ")


def reinit_cluster():
    shutil.rmtree(cluster_dir, ignore_errors=True)
    os.mkdir(cluster_dir)
    if os.path.isfile("{}/cluster.crt".format(cluster_backup_dir)):
        # reuse the certificates we had before the cluster formation
        shutil.copy(
            "{}/cluster.crt".format(cluster_backup_dir), "{}/cluster.crt".format(cluster_dir)
        )
        shutil.copy(
            "{}/cluster.key".format(cluster_backup_dir), "{}/cluster.key".format(cluster_dir)
        )
    else:
        # This node never joined a cluster. A cluster was formed around it.
        hostname = socket.gethostname()  # type: str
        ip = "127.0.0.1"  # type: str
        shutil.copy(
            "{}/certs/csr-dqlite.conf.template".format(snap_path),
            "{}/var/tmp/csr-dqlite.conf".format(snapdata_path),
        )
        subprocess.check_call(
            "{}/bin/sed -i s/HOSTNAME/{}/g {}/var/tmp/csr-dqlite.conf".format(
                snap_path, hostname, snapdata_path
            ).split(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.check_call(
            "{}/bin/sed -i s/HOSTIP/{}/g  {}/var/tmp/csr-dqlite.conf".format(
                snap_path, ip, snapdata_path
            ).split(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.check_call(
            "{0}/openssl.wrapper req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes "
            "-keyout {1}/var/kubernetes/backend/cluster.key "
            "-out {1}/var/kubernetes/backend/cluster.crt "
            "-subj /CN=k8s -config {1}/var/tmp/csr-dqlite.conf -extensions v3_ext".format(
                snap_path, snapdata_path
            ).split(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    # We reset to the default port and address
    init_data = {"Address": "127.0.0.1:19001"}
    with open("{}/init.yaml".format(cluster_dir), "w") as f:
        yaml.dump(init_data, f)


def is_leader_without_successor():
    """Checks if the current node is safe to be removed.

    Check if this node acts as a leader to a cluster with more than one nodes where there
    is no other node to take over the leadership.

    :return: True if this node is the leader without a successor.
    """
    out = subprocess.check_output(
        "{snappath}/bin/dqlite -s file://{dbdir}/cluster.yaml -c {dbdir}/cluster.crt "
        "-k {dbdir}/cluster.key -f json k8s .cluster".format(
            snappath=snap_path, dbdir=cluster_dir
        ).split()
    )
    voters = 0
    data = json.loads(out.decode())
    ep_addresses = []
    for ep in data:
        ep_addresses.append((ep["Address"], ep["Role"]))
        # Role == 0 means we are voters
        if ep["Role"] == 0:
            voters += 1

    local_ips = []
    for interface in netifaces.interfaces():
        if netifaces.AF_INET not in netifaces.ifaddresses(interface):
            continue
        for link in netifaces.ifaddresses(interface)[netifaces.AF_INET]:
            local_ips.append(link["addr"])

    is_voter = False
    for ep in ep_addresses:
        for ip in local_ips:
            if "{}:".format(ip) in ep[0]:
                # ep[1] == ep[Role] == 0 means we are voters
                if ep[1] == 0:
                    is_voter = True

    if voters == 1 and is_voter and len(ep_addresses) > 1:
        # We have one voter in the cluster and the current node is the only voter
        # and there are other nodes that depend on this node.
        return True
    else:
        return False


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


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
def leave():
    """
    The node will depart from the cluster it is in.
    """
    if is_node_running_dqlite():
        if is_node_dqlite_worker():
            reset_current_dqlite_worker_installation()
        else:
            reset_current_dqlite_installation()
    else:
        reset_current_etcd_installation()
    sys.exit(0)


if __name__ == "__main__":
    leave(prog_name="microk8s leave")
