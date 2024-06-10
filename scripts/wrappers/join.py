#!/usr/bin/python3
import hashlib
import http
import json
import os
import random
import shutil
import socket
import ssl
import string
import subprocess
import sys
import time
import ipaddress

import click
import requests
import urllib3
import yaml
from common.cluster.utils import (
    ca_one_line,
    enable_token_auth,
    get_cluster_agent_port,
    get_cluster_cidr,
    get_token,
    get_valid_connection_parts,
    is_low_memory_guard_enabled,
    is_node_running_dqlite,
    is_token_auth_enabled,
    mark_no_cert_reissue,
    rebuild_x509_auth_client_configs,
    service,
    set_arg,
    try_initialise_cni_autodetect_for_clustering,
    try_set_file_permissions,
    snap,
    snap_data,
    FINGERPRINT_MIN_LEN,
    InvalidConnectionError,
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


def get_traefik_port():
    """
    Return the port Traefik listens to. Try read the port from the Traefik configuration or return the default value
    """
    config_file = "{}/args/traefik/traefik-template.yaml".format(snapdata_path)
    with open(config_file) as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
        if (
            "entryPoints" in data
            and "apiserver" in data["entryPoints"]
            and "address" in data["entryPoints"]["apiserver"]
        ):
            port = data["entryPoints"]["apiserver"]["address"]
            port = port.replace(":", "")
            return port
        else:
            return "16443"


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
    worker=False,
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
    :param worker: this is a worker only node

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
                "hostname": socket.gethostname().lower(),
                "port": cluster_agent_port,
                "worker": worker,
                "can_handle_x509_auth": True,
                "can_handle_custom_etcd": True,
            }

            return join_request(conn, CLUSTER_API_V2, req_data, master_ip, verify_peer, fingerprint)
        else:
            req_data = {
                "token": token,
                "hostname": socket.gethostname().lower(),
                "port": cluster_agent_port,
                "callback": callback_token,
                "can_handle_x509_auth": True,
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


def get_etcd_client_cert(master_ip, master_port, token):
    """
    Get a signed cert to access etcd

    :param master_ip: master ip
    :param master_port: master port
    :param token: token to contact the master with
    """
    cer_req_file = "{}/certs/server.remote.csr".format(snapdata_path)
    cmd_cert = (
        "{snap}/openssl.wrapper req -new -sha256 -key {snapdata}/certs/server.key -out {csr} "
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


def get_client_cert(master_ip, master_port, fname: str, token: str, subject: str, with_sans: bool):
    """
    Get a signed cert signed by a remote cluster-agent.
    See https://kubernetes.io/docs/reference/access-authn-authz/authentication/#x509-client-certs

    :param master_ip: master ip
    :param master_port: master port
    :param fname: file name prefix for the certificate
    :param token: token to contact the master with
    :param subject: the subject of the certificate
    :param with_sans: whether to include hostname and node IPs as subject alternate names
    """

    cert_crt = (snap_data() / "certs" / fname).with_suffix(".crt")
    cert_key = (snap_data() / "certs" / fname).with_suffix(".key")
    # generate csr
    script = "generate_csr_with_sans" if with_sans else "generate_csr"
    p = subprocess.run(
        [f"{snap()}/actions/common/utils.sh", script, subject, cert_key],
        check=True,
        capture_output=True,
    )
    csr = p.stdout.decode()

    req_data = {"token": token, "request": csr}
    # TODO: enable ssl verification
    signed = requests.post(
        "https://{}:{}/{}/sign-cert".format(master_ip, master_port, CLUSTER_API),
        json=req_data,
        verify=False,
    )
    if signed.status_code != 200:
        error = "Failed to sign {} certificate ({}).".format(fname, signed.status_code)
        try:
            if "error" in signed.json():
                error = "{} {}".format(error, format(signed.json()["error"]))
        except ValueError:
            print("Make sure the cluster you connect to supports joining worker nodes.")
        print(error)
        exit(1)
    info = signed.json()
    cert_crt.write_text(info["certificate"])
    try_set_file_permissions(cert_crt)


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
    config_template = "{}/{}".format(snap_path, "kubelet.config.template")
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


def update_kubeproxy(token, ca, master_ip, api_port):
    """
    Configure the kube-proxy

    :param token: the token to be in the kubeconfig
    :param ca: the ca
    :param master_ip: the master node IP
    :param api_port: the API server port
    """
    create_kubeconfig(token, ca, master_ip, api_port, "proxy.config", "kubeproxy")
    set_arg("--master", None, "kube-proxy")
    set_arg("--hostname-override", None, "kube-proxy")
    service("restart", "proxy")


def update_cert_auth_kubeproxy(token, master_ip, master_port):
    """
    Configure the kube-proxy

    :param token: the token to be in the kubeconfig
    :param ca: the ca
    :param master_ip: the master node IP
    :param master_port: the master node port where the cluster agent listens
    """
    proxy_token = "{}-proxy".format(token)
    get_client_cert(master_ip, master_port, "proxy", proxy_token, "/CN=system:kube-proxy", False)
    set_arg("--master", None, "kube-proxy")
    set_arg("--hostname-override", None, "kube-proxy")


def update_kubeproxy_cidr(cidr):
    if cidr is not None:
        set_arg("--cluster-cidr", cidr, "kube-proxy")
        service("restart", "proxy")


def update_cert_auth_kubelet(token, master_ip, master_port):
    """
    Configure the kubelet

    :param token: the token to be in the kubeconfig
    :param ca: the ca
    :param master_ip: the master node IP
    :param master_port: the master node port where the cluster agent listens
    """
    kubelet_token = "{}-kubelet".format(token)
    subject = f"/CN=system:node:{socket.gethostname().lower()}/O=system:nodes"
    get_client_cert(master_ip, master_port, "kubelet", kubelet_token, subject, True)
    set_arg("--client-ca-file", "${SNAP_DATA}/certs/ca.remote.crt", "kubelet")
    set_arg(
        "--node-labels",
        "microk8s.io/cluster=true,node.kubernetes.io/microk8s-worker=microk8s-worker",
        "kubelet",
    )


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
    set_arg(
        "--node-labels",
        "microk8s.io/cluster=true,node.kubernetes.io/microk8s-worker=microk8s-worker",
        "kubelet",
    )
    service("restart", "kubelet")


def update_apiserver(api_authz_mode, apiserver_port):
    """
    Configure the API server

    :param api_authz_mode: the authorization mode to be used
    :param apiserver_port: the apiserver port
    """
    if api_authz_mode:
        set_arg("--authorization-mode", api_authz_mode, "kube-apiserver")
    if apiserver_port:
        set_arg("--secure-port", apiserver_port, "kube-apiserver")
    service("restart", "apiserver")


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
    locks = ["clustered.lock", "no-k8s-dqlite"]
    for lock in locks:
        lock_file = "{}/var/lock/{}".format(snapdata_path, lock)
        open(lock_file, "a").close()
        os.chmod(lock_file, 0o700)
    services = ["kubelite", "etcd", "apiserver-kicker", "apiserver-proxy", "k8s-dqlite"]
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


def update_kubelet_node_ip(args_string, hostname_override):
    """
    Update the kubelet --node-ip argument if it was set on the node that we join.

    :param args_string: the kubelet arguments
    :param hostname_override: the source IP address used by the node when joining
    """
    if "--node-ip" in args_string:
        set_arg("--node-ip", hostname_override, "kubelet")


def update_kubelet_hostname_override(args_string):
    """
    Remove the kubelet --hostname-override argument if it was set on the node that we join.

    :param args_string: the kubelet arguments
    """
    if "--hostname-override" in args_string:
        set_arg("--hostname-override", None, "kubelet")


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


def store_cert(filename, payload):
    """
    Store a certificate

    :param filename: where to store the certificate
    :param payload: certificate payload
    """
    file_with_path = "{}/certs/{}".format(snapdata_path, filename)
    if os.path.exists(file_with_path):
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
    config_template = "{}/{}".format(snap_path, "client.config.template")
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

    :param token: the callback token
    """
    callback_token_file = "{}/credentials/callback-token.txt".format(snapdata_path)
    with open(callback_token_file, "w") as fp:
        fp.write(token)
    try_set_file_permissions(callback_token_file)


def update_dqlite(cluster_cert, cluster_key, voters, host):
    """
    Configure the dqlite cluster

    :param cluster_cert: the dqlite cluster cert
    :param cluster_key: the dqlite cluster key
    :param voters: the dqlite voters
    :param host: the hostname others see of this node
    """
    service("stop", "apiserver")
    service("stop", "k8s-dqlite")
    # will allow for apiservice-kicker to generate new certificates @5s loop rate
    time.sleep(10)
    shutil.rmtree(cluster_backup_dir, ignore_errors=True)
    shutil.move(cluster_dir, cluster_backup_dir)
    os.mkdir(cluster_dir)
    store_cluster_certs(cluster_cert, cluster_key)

    # We get the dqlite port from the already existing deployment
    port = 19001
    try:
        with open("{}/info.yaml".format(cluster_backup_dir)) as f:
            data = yaml.safe_load(f)
        if "Address" in data:
            port = data["Address"].rsplit(":")[-1]
    except OSError:
        pass

    # If host is an IPv6 address, wrap it in square brackets
    try:
        if ipaddress.ip_address(host).version == 6:
            host = "[{}]".format(host)
    except ValueError:
        pass

    init_data = {"Cluster": voters, "Address": "{}:{}".format(host, port)}
    with open("{}/init.yaml".format(cluster_dir), "w") as f:
        yaml.dump(init_data, f)

    service("start", "k8s-dqlite")

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
                stderr=subprocess.STDOUT,
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

    # start kube-apiserver after dqlite comes up
    service("start", "apiserver")


def join_dqlite(connection_parts, verify=False, worker=False):
    """
    Configure node to join a dqlite cluster.

    :param connection_parts: connection string parts
    """
    token = connection_parts[1]
    master_ep = connection_parts[0].rsplit(":", 1)
    master_ip = master_ep[0]
    master_port = master_ep[1]
    fingerprint = None
    if len(connection_parts) > 2:
        fingerprint = connection_parts[2]
    else:
        # we do not have a fingerprint, do not attempt to verify the remote cert
        verify = False

    print("Contacting cluster at {}".format(master_ip))

    info = get_connection_info(
        master_ip,
        master_port,
        token,
        cluster_type="dqlite",
        verify_peer=verify,
        fingerprint=fingerprint,
        worker=worker,
    )

    # Get the cluster_cidr from kube-proxy args
    cluster_cidr = get_cluster_cidr()

    if "cluster_cidr" in info and info["cluster_cidr"] != cluster_cidr:
        print(
            "WARNING: Joining a cluster that has a different CIDR. "
            "The kube-proxy CIDR configuration will be overwritten."
        )
        print(
            f"Cluster CIDR: {info['cluster_cidr']} -- Node CIDR: {cluster_cidr}(will be overwritten)"
        )
        update_kubeproxy_cidr(info["cluster_cidr"])

    if worker:
        join_dqlite_worker_node(info, master_ip, master_port, token)
    else:
        join_dqlite_master_node(info, master_ip)


def update_apiserver_proxy(master_ip, api_port):
    """
    Update the apiserver-proxy configuration
    """
    lock_path = os.path.expandvars("${SNAP_DATA}/var/lock")
    lock = "{}/no-apiserver-proxy".format(lock_path)
    if os.path.exists(lock):
        os.remove(lock)

    # add the initial control plane endpoint
    addresses = [{"address": "{}:{}".format(master_ip, api_port)}]

    traefik_providers = os.path.expandvars("${SNAP_DATA}/args/traefik/provider-template.yaml")
    traefik_providers_out = os.path.expandvars("${SNAP_DATA}/args/traefik/provider.yaml")
    with open(traefik_providers) as f:
        p = yaml.safe_load(f)
        p["tcp"]["services"]["kube-apiserver"]["loadBalancer"]["servers"] = addresses
        with open(traefik_providers_out, "w") as out_file:
            yaml.dump(p, out_file)

    try_set_file_permissions(traefik_providers_out)
    service("restart", "apiserver-proxy")


def rebuild_token_based_auth_configs(info):
    # We need to make sure token-auth is enabled in this node too.
    if not is_token_auth_enabled():
        enable_token_auth(info["admin_token"])
    else:
        replace_admin_token(info["admin_token"])

    subprocess.check_call(
        [f"{snap_path}/actions/common/utils.sh", "create_user_certs_and_configs"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def print_worker_usage():
    """
    Print Worker usage
    """
    print("")
    print("The node has joined the cluster and will appear in the nodes list in a few seconds.")
    print("")
    print("This worker node gets automatically configured with the API server endpoints.")
    print(
        "If the API servers are behind a loadbalancer please set the '--refresh-interval' to '0s' in:"
    )
    print("    /var/snap/microk8s/current/args/apiserver-proxy")
    print("and replace the API server endpoints with the one provided by the loadbalancer in:")
    print("    /var/snap/microk8s/current/args/traefik/provider.yaml")
    print("")


def join_dqlite_worker_node(info, master_ip, master_port, token):
    """
    Join this node as a worker to a cluster running dqlite.

    :param info: dictionary with the connection information
    :param master_ip: the IP of the master node we contacted to connect to the cluster
    :param master_port: the port of the mester node we contacted to connect to the cluster
    :param token: the token to pass to the master in order to authenticate with it
    """
    hostname_override = info["hostname_override"]
    if info["ca_key"] is not None:
        print(
            "Joining process failed. Make sure the cluster you connect to supports joining worker nodes."
        )
        exit(1)

    store_remote_ca(info["ca"])

    update_apiserver(info.get("api_authz_mode"), info.get("apiport"))
    store_base_kubelet_args(info["kubelet_args"])
    update_kubelet_node_ip(info["kubelet_args"], hostname_override)
    update_kubelet_hostname_override(info["kubelet_args"])
    update_cert_auth_kubeproxy(token, master_ip, master_port)
    update_cert_auth_kubelet(token, master_ip, master_port)
    subprocess.check_call(
        [f"{snap()}/actions/common/utils.sh", "create_worker_kubeconfigs"],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )

    store_callback_token(info["callback_token"])
    update_apiserver_proxy(master_ip, info["apiport"])
    mark_worker_node()
    mark_no_cert_reissue()
    print_worker_usage()


def join_dqlite_master_node(info, master_ip):
    """
    Join this node to a cluster running dqlite.

    :param info: dictionary with the connection information
    :param master_ip: the IP of the master node we contacted to connect to the cluster
    """

    # The cluster we want to join may be either token-auth based or x509-auth based.
    # The way to identify the cluster type is to look for the "admin_token" in the info
    # we got back from the cluster we try to join.
    # In the case of token-auth we need to:
    # - create the known_tokens.csv file (if it does not exist) with the admin token
    # - turn on token-auth on kube-apiserver
    # - create the token based admin kubeconfig
    # - recreate the kubelet, proxy, scheduler, controller kubeconfigs for the new ca
    # - restart kubelite
    # In the case of x509-auth we need to:
    # - recreate the admin/client, kubelet, proxy, scheduler, controller kubeconfigs for the new ca
    # - restart kubelite

    hostname_override = info["hostname_override"]
    store_cert("ca.crt", info["ca"])
    store_cert("ca.key", info["ca_key"])
    store_cert("serviceaccount.key", info["service_account_key"])

    if "admin_token" in info:
        # We try to join a cluster where token-auth is in place.
        rebuild_token_based_auth_configs(info)
    else:
        # We are joining a x509-auth based cluster
        rebuild_x509_auth_client_configs()

    update_apiserver(info.get("api_authz_mode"), info.get("apiport"))
    store_base_kubelet_args(info["kubelet_args"])
    update_kubelet_node_ip(info["kubelet_args"], hostname_override)
    update_kubelet_hostname_override(info["kubelet_args"])
    store_callback_token(info["callback_token"])

    if "etcd_servers" in info:
        set_arg("--etcd-servers", info["etcd_servers"], "kube-apiserver")
        if info.get("etcd_ca"):
            store_cert("remote-etcd-ca.crt", info["etcd_ca"])
            set_arg("--etcd-cafile", "${SNAP_DATA}/certs/remote-etcd-ca.crt", "kube-apiserver")
        if info.get("etcd_cert"):
            store_cert("remote-etcd.crt", info["etcd_cert"])
            set_arg("--etcd-certfile", "${SNAP_DATA}/certs/remote-etcd.crt", "kube-apiserver")
        if info.get("etcd_key"):
            store_cert("remote-etcd.key", info["etcd_key"])
            set_arg("--etcd-keyfile", "${SNAP_DATA}/certs/remote-etcd.key", "kube-apiserver")

        mark_no_dqlite()
        service("restart", "k8s-dqlite")
        service("restart", "apiserver")
    else:
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
    master_ep = connection_parts[0].rsplit(":", 1)
    master_ip = master_ep[0]
    master_port = master_ep[1]
    callback_token = generate_callback_token()
    info = get_connection_info(master_ip, master_port, token, callback_token=callback_token)

    # check api authn mode from response. default is fallback to Token
    api_authn_mode = info.get("api_authn_mode", "Token")
    if api_authn_mode not in ["Cert", "Token"]:
        print("Error: Unknown API auth mode '{api_authn_mode}' received from control plane node.")
        print("Please update this MicroK8s node to the latest version before joining.")
        exit(7)

    # Get the cluster_cidr from kube-proxy args
    cluster_cidr = get_cluster_cidr()

    if "cluster_cidr" in info and info["cluster_cidr"] != cluster_cidr:
        print(
            "WARNING: Joining a cluster that has a different CIDR. "
            "The kube-proxy CIDR configuration will be overwritten."
        )
        print(
            f"Cluster CIDR: {info['cluster_cidr']} -- Node CIDR: {cluster_cidr}(will be overwritten)"
        )
        update_kubeproxy_cidr(info["cluster_cidr"])

    store_base_kubelet_args(info["kubelet_args"])
    update_kubelet_hostname_override(info["kubelet_args"])
    hostname_override = None
    if "hostname_override" in info:
        hostname_override = info["hostname_override"]
        update_kubelet_node_ip(info["kubelet_args"], hostname_override)

    store_remote_ca(info["ca"])
    update_flannel(info["etcd"], master_ip, master_port, token)

    if api_authn_mode == "Token":
        update_kubeproxy(info["kubeproxy"], info["ca"], master_ip, info["apiport"])
        update_kubelet(info["kubelet"], info["ca"], master_ip, info["apiport"])
    elif api_authn_mode == "Cert":
        update_cert_auth_kubeproxy(info["kubeproxy"], master_ip, master_port)
        update_cert_auth_kubelet(info["kubelet"], master_ip, master_port)
        subprocess.check_call(
            [
                f"{snap()}/actions/common/utils.sh",
                "create_worker_kubeconfigs",
                master_ip,
                info["apiport"],
            ],
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )
    else:
        assert False, "this should never happen"

    mark_worker_node()
    mark_no_cert_reissue()


def mark_join_in_progress():
    """
    Mark node as currently being in the process of joining a cluster.
    """
    lock_file = "{}/var/lock/join-in-progress".format(snapdata_path)
    open(lock_file, "a").close()
    os.chmod(lock_file, 0o700)


def unmark_join_in_progress():
    """
    Unmark as joining cluster; join operation has finished.
    """
    lock_file = "{}/var/lock/join-in-progress".format(snapdata_path)
    if os.path.exists(lock_file):
        os.unlink(lock_file)


def mark_no_dqlite():
    """
    Mark node to not run k8s-dqlite service.
    """
    lock_file = "{}/var/lock/no-k8s-dqlite".format(snapdata_path)
    open(lock_file, "a").close()
    os.chmod(lock_file, 0o700)


@click.command(
    context_settings={"ignore_unknown_options": True, "help_option_names": ["-h", "--help"]}
)
@click.argument("connection", required=True)
@click.option(
    "--worker", "worker", default=False, flag_value="as-worker", help="Join as a worker only node."
)
@click.option(
    "--controlplane",
    "worker",
    flag_value="as-master",
    help="Join running the control plane on HA clusters. (default)",
)
@click.option(
    "--skip-verify",
    is_flag=True,
    required=False,
    default=False,
    help="Skip the certificate verification of the node we are joining to. (default: false)",
)
@click.option(
    "--disable-low-memory-guard",
    is_flag=True,
    required=False,
    default=False,
    help="Disable the low memory guard. (default: false)",
)
def join(connection, worker, skip_verify, disable_low_memory_guard):
    """
    Join the node to a cluster

    CONNECTION: the cluster connection endpoint in format <master>:<port>/<token>
    """
    try:
        connection_parts = get_valid_connection_parts(connection)
    except InvalidConnectionError as err:
        print("Invalid connection:", err)
        sys.exit(1)

    verify = not skip_verify

    if is_low_memory_guard_enabled() and disable_low_memory_guard:
        os.remove(os.path.expandvars("$SNAP_DATA/var/lock/low-memory-guard.lock"))

    if is_low_memory_guard_enabled() and not worker:
        print(
            """
This node does not have enough RAM to host the Kubernetes control plane services
and join the database quorum. You may consider joining this node as a worker instead:

    microk8s join {connection} --worker

If you would still like to join the cluster as a control plane node, use:

    microk8s join {connection} --disable-low-memory-guard

""".format(
                connection=connection
            )
        )
        sys.exit(1)

    mark_join_in_progress()

    if is_node_running_dqlite():
        join_dqlite(connection_parts, verify, worker)
    else:
        join_etcd(connection_parts, verify)

    unmark_join_in_progress()
    print("Successfully joined the cluster.")
    sys.exit(0)


if __name__ == "__main__":
    join(prog_name="microk8s join")
