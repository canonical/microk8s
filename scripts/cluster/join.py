#!/usr/bin/python3
import base64
import random
import string
import subprocess
import os
import ssl
import sys
import time
import hashlib
import http

import click
import requests
import socket
import shutil
import urllib3
import yaml
import json

from common.utils import (
    is_low_memory_guard_enabled,
    try_set_file_permissions,
    is_node_running_dqlite,
    get_cluster_agent_port,
    try_initialise_cni_autodetect_for_clustering,
    service,
    mark_no_cert_reissue,
    restart_all_services,
    get_token,
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
                "hostname": socket.gethostname(),
                "port": cluster_agent_port,
                "worker": worker,
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
                        back_fp.write("{}={}\n".format(key, value))
                else:
                    back_fp.write("{}".format(line))
        if not done and value is not None:
            back_fp.write("{}={}\n".format(key, value))

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


def get_client_cert(master_ip, master_port, fname, token, username, group=None):
    """
    Get a signed cert.
    See https://kubernetes.io/docs/reference/access-authn-authz/authentication/#x509-client-certs

    :param master_ip: master ip
    :param master_port: master port
    :param fname: file name prefix for the certificate
    :param token: token to contact the master with
    :param username: the username of the cert's owner
    :param group: the group the owner belongs to
    """
    info = "/CN={}".format(username)
    if group:
        info = "{}/O={}".format(info, group)
    cer_req_file = "/var/snap/microk8s/current/certs/{}.csr".format(fname)
    cer_key_file = "/var/snap/microk8s/current/certs/{}.key".format(fname)
    cer_file = "/var/snap/microk8s/current/certs/{}.crt".format(fname)
    if not os.path.exists(cer_key_file):
        cmd_gen_cert_key = "{snap}/usr/bin/openssl genrsa -out {key} 2048".format(
            snap=snap_path, key=cer_key_file
        )
        subprocess.check_call(
            cmd_gen_cert_key.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        try_set_file_permissions(cer_key_file)

    cmd_cert = "{snap}/usr/bin/openssl req -new -sha256 -key {key} -out {csr} -subj {info}".format(
        snap=snap_path,
        snapdata=snapdata_path,
        key=cer_key_file,
        csr=cer_req_file,
        info=info,
    )
    subprocess.check_call(cmd_cert.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
            error = "Failed to sign {} certificate ({}).".format(fname, signed.status_code)
            try:
                if "error" in signed.json():
                    error = "{} {}".format(error, format(signed.json()["error"]))
            except ValueError:
                print("Make sure the cluster you connect to supports joining worker nodes.")
            print(error)
            exit(1)
        info = signed.json()
        with open(cer_file, "w") as cert_fp:
            cert_fp.write(info["certificate"])
        try_set_file_permissions(cer_file)

        return {
            "certificate_location": cer_file,
            "certificate_key_location": cer_key_file,
        }


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


def create_x509_kubeconfig(ca, master_ip, api_port, filename, user, path_to_cert, path_to_cert_key):
    """
    Create a kubeconfig file. The file in stored under credentials named after the user

    :param ca: the ca
    :param master_ip: the master node IP
    :param api_port: the API server port
    :param filename: the name of the config file
    :param user: the user to use al login
    :param path_to_cert: path to certificate file
    :param path_to_cert_key: path to certificate key file
    """
    snap_path = os.environ.get("SNAP")
    config_template = "{}/microk8s-resources/{}".format(snap_path, "client-x509.config.template")
    config = "{}/credentials/{}".format(snapdata_path, filename)
    shutil.copyfile(config, "{}.backup".format(config))
    try_set_file_permissions("{}.backup".format(config))
    ca_line = ca_one_line(ca)
    with open(config_template, "r") as tfp:
        with open(config, "w+") as fp:
            config_txt = tfp.read()
            config_txt = config_txt.replace("CADATA", ca_line)
            config_txt = config_txt.replace("NAME", user)
            config_txt = config_txt.replace("PATHTOCERT", path_to_cert)
            config_txt = config_txt.replace("PATHTOKEYCERT", path_to_cert_key)
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


def update_cert_auth_kubeproxy(token, ca, master_ip, master_port, hostname_override):
    """
    Configure the kube-proxy

    :param token: the token to be in the kubeconfig
    :param ca: the ca
    :param master_ip: the master node IP
    :param master_port: the master node port where the cluster agent listens
    :param hostname_override: the hostname override in case the hostname is not resolvable
    """
    proxy_token = "{}-proxy".format(token)
    traefik_port = get_traefik_port()
    cert = get_client_cert(master_ip, master_port, "kube-proxy", proxy_token, "system:kube-proxy")
    create_x509_kubeconfig(
        ca,
        "127.0.0.1",
        traefik_port,
        "proxy.config",
        "kubeproxy",
        cert["certificate_location"],
        cert["certificate_key_location"],
    )
    set_arg("--master", None, "kube-proxy")
    if hostname_override:
        set_arg("--hostname-override", hostname_override, "kube-proxy")
    service("restart", "proxy")


def update_cert_auth_kubelet(token, ca, master_ip, master_port):
    """
    Configure the kubelet

    :param token: the token to be in the kubeconfig
    :param ca: the ca
    :param master_ip: the master node IP
    :param master_port: the master node port where the cluster agent listens
    """
    traefik_port = get_traefik_port()
    kubelet_token = "{}-kubelet".format(token)
    kubelet_user = "system:node:{}".format(socket.gethostname())
    cert = get_client_cert(
        master_ip, master_port, "kubelet", kubelet_token, kubelet_user, "system:nodes"
    )
    create_x509_kubeconfig(
        ca,
        "127.0.0.1",
        traefik_port,
        "kubelet.config",
        "kubelet",
        cert["certificate_location"],
        cert["certificate_key_location"],
    )
    set_arg("--client-ca-file", "${SNAP_DATA}/certs/ca.remote.crt", "kubelet")
    set_arg(
        "--node-labels",
        "microk8s.io/cluster=true,node.kubernetes.io/microk8s-worker=microk8s-worker",
        "kubelet",
    )
    service("restart", "kubelet")


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
    services = ["kubelite", "etcd", "apiserver-kicker", "traefik", "k8s-dqlite"]
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
    time.sleep(10)
    shutil.rmtree(cluster_backup_dir, ignore_errors=True)
    shutil.move(cluster_dir, cluster_backup_dir)
    os.mkdir(cluster_dir)
    store_cluster_certs(cluster_cert, cluster_key)

    # We get the dqlite port from the already existing deployment
    port = 19001
    with open("{}/info.yaml".format(cluster_backup_dir)) as f:
        data = yaml.safe_load(f)
    if "Address" in data:
        port = data["Address"].split(":")[1]

    init_data = {"Cluster": voters, "Address": "{}:{}".format(host, port)}
    with open("{}/init.yaml".format(cluster_dir), "w") as f:
        yaml.dump(init_data, f)

    service("start", "k8s-dqlite")
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

    with open("{}//certs/csr.conf".format(snapdata_path), "w") as f:
        f.write("changeme")

    restart_all_services()


def join_dqlite(connection_parts, verify=False, worker=False):
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
        worker=worker,
    )

    if worker:
        join_dqlite_worker_node(info, master_ip, master_port, token)
    else:
        join_dqlite_master_node(info, master_ip, token)


def update_traefik(master_ip, api_port, nodes_ips):
    """
    Update the traefik configuration
    """
    lock_path = os.path.expandvars("${SNAP_DATA}/var/lock")
    lock = "{}/no-traefik".format(lock_path)
    if os.path.exists(lock):
        os.remove(lock)

    # add the addresses where we expect to find the API servers
    addresses = []
    # first the node we contact
    addresses.append({"address": "{}:{}".format(master_ip, api_port)})
    # then all the nodes assuming the default port
    for n in nodes_ips:
        if n == master_ip:
            continue
        addresses.append({"address": "{}:{}".format(n, api_port)})

    traefik_providers = os.path.expandvars("${SNAP_DATA}/args/traefik/provider-template.yaml")
    traefik_providers_out = os.path.expandvars("${SNAP_DATA}/args/traefik/provider.yaml")
    with open(traefik_providers) as f:
        p = yaml.safe_load(f)
        p["tcp"]["services"]["kube-apiserver"]["loadBalancer"]["servers"] = addresses
        with open(traefik_providers_out, "w") as out_file:
            yaml.dump(p, out_file)
    try_set_file_permissions(traefik_providers_out)
    service("restart", "traefik")


def print_traefik_usage(master_ip, api_port, nodes_ips):
    """
    Print Traefik usage
    """
    print("")
    print("The node has joined the cluster and will appear in the nodes list in a few seconds.")
    print("")
    print(
        "Currently this worker node is configured with the following kubernetes API server endpoints:"
    )
    print(
        "    - {} and port {}, this is the cluster node contacted during the join operation.".format(
            master_ip, api_port
        )
    )
    for n in nodes_ips:
        if n == master_ip:
            continue
        print("    - {} assuming port {}".format(n, api_port))
    print("")
    print(
        "If the above endpoints are incorrect, incomplete or if the API servers are behind a loadbalancer please update"
    )
    print("/var/snap/microk8s/current/args/traefik/provider.yaml")
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
    store_cert("serviceaccount.key", info["service_account_key"])

    store_base_kubelet_args(info["kubelet_args"])

    update_cert_auth_kubeproxy(token, info["ca"], master_ip, master_port, hostname_override)
    update_cert_auth_kubelet(token, info["ca"], master_ip, master_port)

    store_callback_token(info["callback_token"])
    update_traefik(master_ip, info["apiport"], info["control_plane_nodes"])
    mark_worker_node()
    mark_no_cert_reissue()
    print_traefik_usage(master_ip, info["apiport"], info["control_plane_nodes"])


def join_dqlite_master_node(info, master_ip, token):
    """
    Join this node to a cluster running dqlite.

    :param info: dictionary with the connection information
    :param master_ip: the IP of the master node we contacted to connect to the cluster
    :param token: the token to pass to the master in order to authenticate with it
    """
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


@click.command(context_settings={"ignore_unknown_options": True})
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
    connection_parts = connection.split("/")
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

    if is_node_running_dqlite():
        join_dqlite(connection_parts, verify, worker)
    else:
        join_etcd(connection_parts, verify)
    sys.exit(0)


if __name__ == "__main__":
    join(prog_name="microk8s join")
