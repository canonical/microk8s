#!/usr/bin/python3
import base64
import random
import string
import subprocess
import os
import getopt
import ssl
import sys
import time
import hashlib
import http

import netifaces
import requests
import socket
import shutil
import urllib3
import yaml
import json

from common.utils import (
    try_set_file_permissions,
    is_node_running_dqlite,
    get_cluster_agent_port,
    try_initialise_cni_autodetect_for_clustering,
    service,
    mark_no_cert_reissue,
    unmark_no_cert_reissue,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
CLUSTER_API = "cluster/api/v1.0"
snapdata_path = os.environ.get("SNAP_DATA")
snap_path = os.environ.get("SNAP")
ca_cert_file_via_env = "${SNAP_DATA}/certs/ca.remote.crt"
ca_cert_file = "{}/certs/ca.remote.crt".format(snapdata_path)
callback_token_file = "{}/credentials/callback-token.txt".format(snapdata_path)
callback_tokens_file = "{}/credentials/callback-tokens.txt".format(snapdata_path)
server_cert_file_via_env = "${SNAP_DATA}/certs/server.remote.crt"
server_cert_file = "{}/certs/server.remote.crt".format(snapdata_path)

CLUSTER_API_V2 = "cluster/api/v2.0"
cluster_dir = "{}/var/kubernetes/backend".format(snapdata_path)
cluster_backup_dir = "{}/var/kubernetes/backend.backup".format(snapdata_path)
cluster_cert_file = "{}/cluster.crt".format(cluster_dir)
cluster_key_file = "{}/cluster.key".format(cluster_dir)

FINGERPRINT_MIN_LEN = 12


def join_request(conn, api_version, req_data, master_ip, verify_peer, fingerprint):
    json_params = json.dumps(req_data)
    headers = {"Content-type": "application/json", "Accept": "application/json"}

    try:
        if verify_peer and fingerprint:
            if len(fingerprint) < FINGERPRINT_MIN_LEN:
                print(
                    "Joining cluster failed. Fingerprint too short."
                    " Use '--skip-verify' to skip server certificate check."
                )
                exit(4)

            # Do the peer certificate verification
            der_cert_bin = conn.sock.getpeercert(True)
            peer_cert_hash = hashlib.sha256(der_cert_bin).hexdigest()
            if not peer_cert_hash.startswith(fingerprint):
                print(
                    "Joining cluster failed. Could not verify the identity of {}."
                    " Use '--skip-verify' to skip server certificate check.".format(master_ip)
                )
                exit(4)

        conn.request("POST", "/{}/join".format(api_version), json_params, headers)
        response = conn.getresponse()
        if not response.status == 200:
            message = extract_error(response)
            print("{} ({}).".format(message, response.status))
            exit(6)
        body = response.read()
        return json.loads(body)
    except http.client.HTTPException as e:
        print("Please ensure the master node is reachable. {}".format(e))
        exit(1)
    except ssl.SSLError as e:
        print("Peer node verification failed ({}).".format(e))
        exit(4)


def extract_error(response):
    message = "Connection failed."
    try:
        resp = response.read().decode()
        if resp:
            res_data = json.loads(resp)
            if "error" in res_data:
                message = "{} {}".format(message, res_data["error"])
    except ValueError:
        pass
    return message


def get_connection_info(
    master_ip,
    master_port,
    token,
    callback_token=None,
    cluster_type="etcd",
    verify_peer=False,
    fingerprint=None,
):
    """
    Contact the master and get all connection information

    :param master_ip: the master IP
    :param master_port: the master port
    :param token: the token to contact the master with
    :param callback_token: callback token for etcd based clusters
    :param cluster_type: the type of cluster we want to join, etcd or dqlite
    :param verify_peer: flag indicating if we should verify peers certificate
    :param fingerprint: the certificate fingerprint we expect from the peer

    :return: the json response of the master
    """
    cluster_agent_port = get_cluster_agent_port()
    try:
        context = ssl._create_unverified_context()
        conn = http.client.HTTPSConnection("{}:{}".format(master_ip, master_port), context=context)
        conn.connect()
        if cluster_type == "dqlite":
            req_data = {
                "token": token,
                "hostname": socket.gethostname(),
                "port": cluster_agent_port,
            }

            return join_request(conn, CLUSTER_API_V2, req_data, master_ip, verify_peer, fingerprint)
        else:
            req_data = {
                "token": token,
                "hostname": socket.gethostname(),
                "port": cluster_agent_port,
                "callback": callback_token,
            }
            return join_request(
                conn, CLUSTER_API, req_data, master_ip, verify_peer=False, fingerprint=None
            )
    except http.client.HTTPException as e:
        print("Connecting to cluster failed with {}.".format(e))
        exit(5)
    except ssl.SSLError as e:
        print("Peer node verification failed with {}.".format(e))
        exit(4)


def usage():
    print("Join a cluster: microk8s join <master>:<port>/<token> [options]")
    print("")
    print("Options:")
    print(
        "--skip-verify  skip the certificate verification of the node we are"
        " joining to (default: false)."
    )


def set_arg(key, value, file):
    """
    Set an argument to a file

    :param key: argument name
    :param value: value
    :param file: the arguments file
    """
    filename = "{}/args/{}".format(snapdata_path, file)
    filename_remote = "{}/args/{}.remote".format(snapdata_path, file)
    done = False
    with open(filename_remote, "w+") as back_fp:
        with open(filename, "r+") as fp:
            for _, line in enumerate(fp):
                if line.startswith(key):
                    done = True
                    if value is not None:
                        back_fp.write("{} {}\n".format(key, value))
                else:
                    back_fp.write("{}".format(line))
        if not done and value is not None:
            back_fp.write("{} {}\n".format(key, value))

    shutil.copyfile(filename, "{}.backup".format(filename))
    try_set_file_permissions("{}.backup".format(filename))
    shutil.copyfile(filename_remote, filename)
    try_set_file_permissions(filename)
    os.remove(filename_remote)


def get_etcd_client_cert(master_ip, master_port, token):
    """
    Get a signed cert to access etcd

    :param master_ip: master ip
    :param master_port: master port
    :param token: token to contact the master with
    """
    cer_req_file = "{}/certs/server.remote.csr".format(snapdata_path)
    cmd_cert = (
        "{snap}/usr/bin/openssl req -new -sha256 -key {snapdata}/certs/server.key -out {csr} "
        "-config {snapdata}/certs/csr.conf".format(
            snap=snap_path, snapdata=snapdata_path, csr=cer_req_file
        )
    )
    subprocess.check_call(cmd_cert.split())
    with open(cer_req_file) as fp:
        csr = fp.read()
        req_data = {"token": token, "request": csr}
        # TODO: enable ssl verification
        signed = requests.post(
            "https://{}:{}/{}/sign-cert".format(master_ip, master_port, CLUSTER_API),
            json=req_data,
            verify=False,
        )
        if signed.status_code != 200:
            print("Failed to sign certificate. {}".format(signed.json()["error"]))
            exit(1)
        info = signed.json()
        with open(server_cert_file, "w") as cert_fp:
            cert_fp.write(info["certificate"])
        try_set_file_permissions(server_cert_file)


def update_flannel(etcd, master_ip, master_port, token):
    """
    Configure flannel

    :param etcd: etcd endpoint
    :param master_ip: master ip
    :param master_port: master port
    :param token: token to contact the master with
    """
    get_etcd_client_cert(master_ip, master_port, token)
    etcd = etcd.replace("0.0.0.0", master_ip)
    set_arg("--etcd-endpoints", etcd, "flanneld")
    set_arg("--etcd-cafile", ca_cert_file_via_env, "flanneld")
    set_arg("--etcd-certfile", server_cert_file_via_env, "flanneld")
    set_arg("--etcd-keyfile", "${SNAP_DATA}/certs/server.key", "flanneld")
    service("restart", "flanneld")


def ca_one_line(ca):
    """
    The CA in one line
    :param ca: the ca
    :return: one line
    """
    return base64.b64encode(ca.encode("utf-8")).decode("utf-8")


def create_kubeconfig(token, ca, master_ip, api_port, filename, user):
    """
    Create a kubeconfig file. The file in stored under credentials named after the user

    :param token: the token to be in the kubeconfig
    :param ca: the ca
    :param master_ip: the master node IP
    :param api_port: the API server port
    :param filename: the name of the config file
    :param user: the user to use al login
    """
    snap_path = os.environ.get("SNAP")
    config_template = "{}/microk8s-resources/{}".format(snap_path, "kubelet.config.template")
    config = "{}/credentials/{}".format(snapdata_path, filename)
    shutil.copyfile(config, "{}.backup".format(config))
    try_set_file_permissions("{}.backup".format(config))
    ca_line = ca_one_line(ca)
    with open(config_template, "r") as tfp:
        with open(config, "w+") as fp:
            config_txt = tfp.read()
            config_txt = config_txt.replace("CADATA", ca_line)
            config_txt = config_txt.replace("NAME", user)
            config_txt = config_txt.replace("TOKEN", token)
            config_txt = config_txt.replace("127.0.0.1", master_ip)
            config_txt = config_txt.replace("16443", api_port)
            fp.write(config_txt)
        try_set_file_permissions(config)


def update_kubeproxy(token, ca, master_ip, api_port, hostname_override):
    """
    Configure the kube-proxy

    :param token: the token to be in the kubeconfig
    :param ca: the ca
    :param master_ip: the master node IP
    :param api_port: the API server port
    :param hostname_override: the hostname override in case the hostname is not resolvable
    """
    create_kubeconfig(token, ca, master_ip, api_port, "proxy.config", "kubeproxy")
    set_arg("--master", None, "kube-proxy")
    if hostname_override:
        set_arg("--hostname-override", hostname_override, "kube-proxy")
    service("restart", "proxy")


def update_kubelet(token, ca, master_ip, api_port):
    """
    Configure the kubelet

    :param token: the token to be in the kubeconfig
    :param ca: the ca
    :param master_ip: the master node IP
    :param api_port: the API server port
    """
    create_kubeconfig(token, ca, master_ip, api_port, "kubelet.config", "kubelet")
    set_arg("--client-ca-file", "${SNAP_DATA}/certs/ca.remote.crt", "kubelet")
    service("restart", "kubelet")


def store_remote_ca(ca):
    """
    Store the remote ca

    :param ca: the CA
    """
    with open(ca_cert_file, "w+") as fp:
        fp.write(ca)
    try_set_file_permissions(ca_cert_file)


def mark_worker_node():
    """
    Mark a node as being part of a cluster not running the control plane
    by creating a var/lock/clustered.lock
    """
    lock_file = "{}/var/lock/clustered.lock".format(snapdata_path)
    open(lock_file, "a").close()
    os.chmod(lock_file, 0o700)
    services = ["etcd", "apiserver-kicker", "kubelite"]
    for s in services:
        service("restart", s)


def generate_callback_token():
    """
    Generate a token and store it in the callback token file

    :return: the token
    """
    token = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(64))
    with open(callback_token_file, "w") as fp:
        fp.write("{}\n".format(token))

    try_set_file_permissions(callback_token_file)
    return token


def store_base_kubelet_args(args_string):
    """
    Create a kubelet args file from the set of args provided

    :param args_string: the arguments provided
    """
    args_file = "{}/args/kubelet".format(snapdata_path)
    with open(args_file, "w") as fp:
        fp.write(args_string)
    try_set_file_permissions(args_file)


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
    time.sleep(10)

    delete_dqlite_node(my_ep, other_ep)

    print("Generating new cluster certificates.", flush=True)
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
            "{}/microk8s-resources/certs/csr-dqlite.conf.template".format(snap_path),
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
            "{0}/usr/bin/openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes "
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

    service("start", "apiserver")

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
    unmark_no_cert_reissue()
    restart_all_services()


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


def replace_admin_token(token):
    """
    Replaces the admin token in the known tokens

    :param token: the admin token
    """
    file = "{}/credentials/known_tokens.csv".format(snapdata_path)
    backup_file = "{}.backup".format(file)
    # That is a critical section. We need to protect it.
    with open(backup_file, "w") as back_fp:
        with open(file, "r") as fp:
            for _, line in enumerate(fp):
                if 'admin,admin,"system:masters"' in line:
                    continue
                back_fp.write("{}".format(line))
            back_fp.write('{},admin,admin,"system:masters"\n'.format(token))

    try_set_file_permissions(backup_file)
    shutil.copyfile(backup_file, file)


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
            for _, line in enumerate(callback_fp):
                parts = line.split()
                if parts[0] == node:
                    continue
                else:
                    backup_fp.write(line)

    try_set_file_permissions(tmp_file)
    shutil.move(tmp_file, callback_tokens_file)


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

    remove_kubelet_token(node)
    remove_callback_token(node)
    subprocess.check_call(
        "{}/microk8s-kubectl.wrapper delete no {}".format(snap_path, node).split(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def remove_dqlite_node(node, force=False):
    try:
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


def get_token(name, tokens_file="known_tokens.csv"):
    """
    Get token from known_tokens file

    :param name: the name of the node
    :param tokens_file: the file where the tokens should go
    :returns: the token or None(if name doesn't exist)
    """
    file = "{}/credentials/{}".format(snapdata_path, tokens_file)
    with open(file) as fp:
        for line in fp:
            if name in line:
                parts = line.split(",")
                return parts[0].rstrip()
    return None


def store_cert(filename, payload):
    """
    Store a certificate

    :param filename: where to store the certificate
    :param payload: certificate payload
    """
    file_with_path = "{}/certs/{}".format(snapdata_path, filename)
    backup_file_with_path = "{}.backup".format(file_with_path)
    shutil.copyfile(file_with_path, backup_file_with_path)
    try_set_file_permissions(backup_file_with_path)
    with open(file_with_path, "w+") as fp:
        fp.write(payload)
    try_set_file_permissions(file_with_path)


def store_cluster_certs(cluster_cert, cluster_key):
    """
    Store the dqlite cluster certs

    :param cluster_cert: the cluster certificate
    :param cluster_key: the cluster certificate key
    """
    with open(cluster_cert_file, "w+") as fp:
        fp.write(cluster_cert)
    try_set_file_permissions(cluster_cert_file)
    with open(cluster_key_file, "w+") as fp:
        fp.write(cluster_key)
    try_set_file_permissions(cluster_key_file)


def create_admin_kubeconfig(ca, ha_admin_token=None):
    """
    Create a kubeconfig file. The file in stored under credentials named after the admin

    :param ca: the ca
    :param ha_admin_token: the ha_cluster_token
    """
    if not ha_admin_token:
        token = get_token("admin", "basic_auth.csv")
        if not token:
            print("Error, could not locate admin token. Joining cluster failed.")
            exit(2)
    else:
        token = ha_admin_token
    assert token is not None
    config_template = "{}/microk8s-resources/{}".format(snap_path, "client.config.template")
    config = "{}/credentials/client.config".format(snapdata_path)
    shutil.copyfile(config, "{}.backup".format(config))
    try_set_file_permissions("{}.backup".format(config))
    ca_line = ca_one_line(ca)
    with open(config_template, "r") as tfp:
        with open(config, "w+") as fp:
            for _, config_txt in enumerate(tfp):
                if config_txt.strip().startswith("username:"):
                    continue
                else:
                    config_txt = config_txt.replace("CADATA", ca_line)
                    config_txt = config_txt.replace("NAME", "admin")
                    config_txt = config_txt.replace("AUTHTYPE", "token")
                    config_txt = config_txt.replace("PASSWORD", token)
                    fp.write(config_txt)
        try_set_file_permissions(config)


def store_callback_token(token):
    """
    Store the callback token

    :param stoken: the callback token
    """
    callback_token_file = "{}/credentials/callback-token.txt".format(snapdata_path)
    with open(callback_token_file, "w") as fp:
        fp.write(token)
    try_set_file_permissions(callback_token_file)


def restart_all_services():
    """
    Restart all services
    """
    waits = 10
    while waits > 0:
        try:
            subprocess.check_call(
                "{}/microk8s-stop.wrapper".format(snap_path).split(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            break
        except subprocess.CalledProcessError:
            time.sleep(5)
            waits -= 1
    waits = 10
    while waits > 0:
        try:
            subprocess.check_call(
                "{}/microk8s-start.wrapper".format(snap_path).split(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            break
        except subprocess.CalledProcessError:
            time.sleep(5)
            waits -= 1


def update_dqlite(cluster_cert, cluster_key, voters, host):
    """
    Configure the dqlite cluster

    :param cluster_cert: the dqlite cluster cert
    :param cluster_key: the dqlite cluster key
    :param voters: the dqlite voters
    :param host: the hostname others see of this node
    """
    service("stop", "apiserver")
    time.sleep(10)
    shutil.rmtree(cluster_backup_dir, ignore_errors=True)
    shutil.move(cluster_dir, cluster_backup_dir)
    os.mkdir(cluster_dir)
    store_cluster_certs(cluster_cert, cluster_key)

    # We get the dqlite port from the already existing deployment
    port = 19001
    with open("{}/info.yaml".format(cluster_backup_dir)) as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    if "Address" in data:
        port = data["Address"].split(":")[1]

    init_data = {"Cluster": voters, "Address": "{}:{}".format(host, port)}
    with open("{}/init.yaml".format(cluster_dir), "w") as f:
        yaml.dump(init_data, f)

    service("start", "apiserver")

    waits = 10
    print("Waiting for this node to finish joining the cluster.", end=" ", flush=True)
    while waits > 0:
        try:
            out = subprocess.check_output(
                "{snappath}/bin/dqlite -s file://{dbdir}/cluster.yaml -c {dbdir}/cluster.crt "
                "-k {dbdir}/cluster.key -f json k8s .cluster".format(
                    snappath=snap_path, dbdir=cluster_dir
                ).split(),
                timeout=4,
            )
            if host in out.decode():
                break
            else:
                print(".", end=" ", flush=True)
                time.sleep(5)
                waits -= 1

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            print("..", end=" ", flush=True)
            time.sleep(2)
            waits -= 1
    print(" ")

    with open("{}//certs/csr.conf".format(snapdata_path), "w") as f:
        f.write("changeme")

    restart_all_services()


def join_dqlite(connection_parts, verify=False):
    """
    Configure node to join a dqlite cluster.

    :param connection_parts: connection string parts
    """
    token = connection_parts[1]
    master_ep = connection_parts[0].split(":")
    master_ip = master_ep[0]
    master_port = master_ep[1]
    fingerprint = None
    if len(connection_parts) > 2:
        fingerprint = connection_parts[2]
        verify = True

    print("Contacting cluster at {}".format(master_ip))

    info = get_connection_info(
        master_ip,
        master_port,
        token,
        cluster_type="dqlite",
        verify_peer=verify,
        fingerprint=fingerprint,
    )

    hostname_override = info["hostname_override"]

    store_cert("ca.crt", info["ca"])
    store_cert("ca.key", info["ca_key"])
    store_cert("serviceaccount.key", info["service_account_key"])
    # triplets of [username in known_tokens.csv, username in kubeconfig, kubeconfig filename name]
    for component in [
        ("kube-proxy", "kubeproxy", "proxy.config"),
        ("kubelet", "kubelet", "kubelet.config"),
        ("kube-controller-manager", "controller", "controller.config"),
        ("kube-scheduler", "scheduler", "scheduler.config"),
    ]:
        component_token = get_token(component[0])
        if not component_token:
            print("Error, could not locate {} token. Joining cluster failed.".format(component[0]))
            exit(3)
        assert token is not None
        # TODO make this configurable
        create_kubeconfig(
            component_token, info["ca"], "127.0.0.1", "16443", component[2], component[1]
        )
    if "admin_token" in info:
        replace_admin_token(info["admin_token"])
    create_admin_kubeconfig(info["ca"], info["admin_token"])
    store_base_kubelet_args(info["kubelet_args"])
    store_callback_token(info["callback_token"])

    update_dqlite(info["cluster_cert"], info["cluster_key"], info["voters"], hostname_override)
    # We want to update the local CNI yaml but we do not want to apply it.
    # The cni is applied already in the cluster we join
    try_initialise_cni_autodetect_for_clustering(master_ip, apply_cni=False)
    mark_no_cert_reissue()

def join_etcd(connection_parts, verify=True):
    """
    Configure node to join an etcd cluster.

    :param connection_parts: connection string parts
    """
    token = connection_parts[1]
    master_ep = connection_parts[0].split(":")
    master_ip = master_ep[0]
    master_port = master_ep[1]
    callback_token = generate_callback_token()
    info = get_connection_info(master_ip, master_port, token, callback_token=callback_token)
    store_base_kubelet_args(info["kubelet_args"])
    hostname_override = None
    if "hostname_override" in info:
        hostname_override = info["hostname_override"]
    store_remote_ca(info["ca"])
    update_flannel(info["etcd"], master_ip, master_port, token)
    update_kubeproxy(info["kubeproxy"], info["ca"], master_ip, info["apiport"], hostname_override)
    update_kubelet(info["kubelet"], info["ca"], master_ip, info["apiport"])
    mark_worker_node()
    mark_no_cert_reissue()


if __name__ == "__main__":
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "hfs", ["help", "force", "skip-verify"])
    except getopt.GetoptError as err:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    force = False
    verify = True
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit(1)
        elif o in ("-f", "--force"):
            force = True
        elif o in ("-s", "--skip-verify"):
            verify = False
        else:
            print("Unhandled option")
            sys.exit(1)

    if len(args) <= 0:
        print("Please provide a connection string.")
        usage()
        sys.exit(4)
    elif args[0] == "reset":
        if len(args) > 1:
            if is_node_running_dqlite():
                remove_dqlite_node(args[1], force)
            else:
                remove_node(args[1])

        else:
            if is_node_running_dqlite():
                reset_current_dqlite_installation()
            else:
                reset_current_etcd_installation()
    else:
        connection_parts = args[0].split("/")
        if is_node_running_dqlite():
            join_dqlite(connection_parts, verify)
        else:
            join_etcd(connection_parts, verify)

    sys.exit(0)
