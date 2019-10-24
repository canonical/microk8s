#!/usr/bin/python3
import base64
import subprocess
import os
import getopt
import sys
import time
from typing import Dict, Optional, List, Tuple

import requests
import socket
import shutil
import urllib3  # type: ignore

from common.utils import try_set_file_permissions, get_callback_token
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
CLUSTER_API = "cluster/api/v1.0"  # type: str
CLUSTER_API_V2 ="cluster/api/v2.0"  # type: str
snapdata_path = os.environ.get('SNAP_DATA')  # type: Optional[str]
snap_path = os.environ.get('SNAP')  # type: Optional[str]
ca_cert_file = "{}/certs/ca.crt".format(snapdata_path)  # type: str
ca_cert_key_file = "{}/certs/ca.key".format(snapdata_path)  # type: str
server_cert_file = "{}/certs/server.crt".format(snapdata_path)  # type: str
server_cert_key_file = "{}/certs/server.key".format(snapdata_path)  # type: str
service_account_key_file = "{}/certs/serviceaccount.key".format(snapdata_path)  # type: str
cluster_dir = "{}/var/kubernetes/backend".format(snapdata_path)  # type: str
cluster_backup_dir = "{}/var/kubernetes/backend.backup".format(snapdata_path)  # type: str
cluster_cert_file = "{}/cluster.crt".format(cluster_dir)  # type: str
cluster_key_file = "{}/cluster.key".format(cluster_dir)  # type: str
callback_token_file = "{}/credentials/callback-token.txt".format(snapdata_path)  # type: str


def get_connection_info(master_ip: str, master_port: str, token: str) -> Dict[str, str]:
    """
    Contact the master and get all connection information

    :param master_ip: the master IP
    :param master_port: the master port
    :param token: the token to contact the master with
    :return: the json response of the master
    """
    cluster_agent_port = "25000"  # type: str
    filename = "{}/args/cluster-agent".format(snapdata_path)  # type: str
    with open(filename) as fp:
        for _, line in enumerate(fp):
            if line.startswith("--port"):
                port_parse = line.split(' ')  # type: List[str]
                port_parse = port_parse[-1].split('=')
                cluster_agent_port = port_parse[0].rstrip()

    req_data = {"token": token,
                "hostname": socket.gethostname(),
                "port": cluster_agent_port}  # type: Dict[str, str]

    # TODO: enable ssl verification
    connection_info = requests.post("https://{}:{}/{}/join".format(master_ip, master_port, CLUSTER_API_V2),
                                    json=req_data,
                                    verify=False)  # type: requests.models.Response
    if connection_info.status_code != 200:
        message = "Error code {}.".format(connection_info.status_code)  # type: str
        if connection_info.headers.get('content-type') == 'application/json':
            res_data = connection_info.json()  # type: Dict[str, str]
            if 'error' in res_data:
                message = "{} {}".format(message, res_data["error"])
        print("Failed to join cluster. {}".format(message))
        exit(1)
    return connection_info.json()


def usage() -> None:
    print("Join a cluster: microk8s.join <master>:<port>/<token>")


def ca_one_line(ca: str) -> str:
    """
    The CA in one line
    :param ca: the ca
    :return: one line
    """
    return base64.b64encode(ca.encode('utf-8')).decode('utf-8')


def create_kubeconfig(token: str, ca: str, master_ip: str, api_port: str, filename: str, user: str) -> None:
    """
    Create a kubeconfig file. The file in stored under credentials named after the user

    :param token: the token to be in the kubeconfig
    :param ca: the ca
    :param master_ip: the master node IP
    :param api_port: the API server port
    :param filename: the name of the config file
    :param user: the user to use al login
    """
    snap_path = os.environ.get('SNAP')  # type: Optional[str]
    config_template = "{}/microk8s-resources/{}".format(snap_path, "kubelet.config.template")  # type: str
    config = "{}/credentials/{}".format(snapdata_path, filename)  # type: str
    shutil.copyfile(config, "{}.backup".format(config))
    try_set_file_permissions("{}.backup".format(config))
    ca_line = ca_one_line(ca)  # type: str
    with open(config_template, 'r') as tfp:
        with open(config, 'w+') as fp:
            config_txt = tfp.read()  # type: str
            config_txt = config_txt.replace("CADATA", ca_line)
            config_txt = config_txt.replace("NAME", user)
            config_txt = config_txt.replace("TOKEN", token)
            config_txt = config_txt.replace("127.0.0.1", master_ip)
            config_txt = config_txt.replace("16443", api_port)
            fp.write(config_txt)
        try_set_file_permissions(config)


def create_admin_kubeconfig(ca: str) ->  None:
    """
    Create a kubeconfig file. The file in stored under credentials named after the admin

    :param ca: the ca
    """
    token = get_token("admin", "basic_auth.csv")  # type: Optional[str]
    if not token:
        print("Error, could not locate admin token. Joining cluster failed.")
        exit(2)
    assert token is not None
    config_template = "{}/microk8s-resources/{}".format(snap_path, "client.config.template")  # type: str
    config = "{}/credentials/client.config".format(snapdata_path)  # type: str
    shutil.copyfile(config, "{}.backup".format(config))
    try_set_file_permissions("{}.backup".format(config))
    ca_line = ca_one_line(ca)  # type: str
    with open(config_template, 'r') as tfp:
        with open(config, 'w+') as fp:
            config_txt = tfp.read()  # type: str
            config_txt = config_txt.replace("CADATA", ca_line)
            config_txt = config_txt.replace("NAME", "admin")
            config_txt = config_txt.replace("AUTHTYPE", "password")
            config_txt = config_txt.replace("PASSWORD", token)
            fp.write(config_txt)
        try_set_file_permissions(config)


def store_cert(filename: str, payload: str) -> None:
    """
    Store a certificate

    :param filename: where to store the certificate
    :param payload: certificate payload
    """
    file_with_path = "{}/certs/{}".format(snapdata_path, filename)  # type: str
    backup_file_with_path = "{}.backup".format(file_with_path)  # type: str
    shutil.copyfile(file_with_path, backup_file_with_path)
    try_set_file_permissions(backup_file_with_path)
    with open(file_with_path, 'w+') as fp:
        fp.write(payload)
    try_set_file_permissions(file_with_path)


def store_cluster_certs(cluster_cert: str, cluster_key: str) -> None:
    """
    Store the dqlite cluster certs

    :param cluster_cert: the cluster certificate
    :param cluster_key: the cluster certificate key
    """
    with open(cluster_cert_file, 'w+') as fp:
        fp.write(cluster_cert)
    try_set_file_permissions(cluster_cert_file)
    with open(cluster_key_file, 'w+') as fp:
        fp.write(cluster_key)
    try_set_file_permissions(cluster_key_file)


def store_base_kubelet_args(args_string: str) -> None:
    """
    Create a kubelet args file from the set of args provided

    :param args_string: the arguments provided
    """
    args_file = "{}/args/kubelet".format(snapdata_path)  # type: str
    with open(args_file, "w") as fp:
        fp.write(args_string)
    try_set_file_permissions(args_file)


def store_callback_token(token: str) -> None:
    """
    Store the callback token

    :param stoken: the callback token
    """
    callback_token_file = "{}/credentials/callback-token.txt".format(snapdata_path)  # type: str
    with open(callback_token_file, "w") as fp:
        fp.write(token)
    try_set_file_permissions(callback_token_file)


def reset_current_installation() -> None:
    """
    Take a node out of a cluster
    """
    subprocess.check_call("systemctl stop snap.microk8s.daemon-apiserver.service".split())
    time.sleep(10)
    shutil.rmtree(cluster_dir, ignore_errors=True)
    os.mkdir(cluster_dir)
    if os.path.isfile("{}/cluster.crt".format(cluster_backup_dir)):
        # reuse the certificates we had before the cluster formation
        shutil.copy("{}/cluster.crt".format(cluster_backup_dir), "{}/cluster.crt".format(cluster_dir))
        shutil.copy("{}/cluster.key".format(cluster_backup_dir), "{}/cluster.key".format(cluster_dir))
    else:
        # This nod never joined a cluster. A cluster was formed around it.
        hostname = socket.gethostname()  # type: str
        ip = '127.0.0.1'  # type: str
        shutil.copy('{}/microk8s-resources/certs/csr-dqlite.conf.template'.format(snap_path),
                    '{}/var/tmp/csr-dqlite.conf'.format(snapdata_path))
        subprocess.check_call("{}/bin/sed -i s/HOSTNAME/{}/g {}/var/tmp/csr-dqlite.conf"
                              .format(snap_path, hostname, snapdata_path).split())
        subprocess.check_call("{}/bin/sed -i s/HOSTIP/{}/g  {}/var/tmp/csr-dqlite.conf"
                              .format(snap_path, ip, snapdata_path).split())
        subprocess.check_call('{0}/usr/bin/openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes '
                              '-keyout {1}/var/kubernetes/backend/cluster.key '
                              '-out {1}/var/kubernetes/backend/cluster.crt '
                              '-subj "/CN=k8s" -config {1}/var/tmp/csr-dqlite.conf -extensions v3_ext'
                              .format(snap_path, snapdata_path).split())

    # TODO make this port configurable
    init_data = {'Address': '127.0.0.1:19001'}  # type: Dict[str, str]
    with open("{}/init.yaml".format(cluster_dir), 'w') as f:
        yaml.dump(init_data, f)

    subprocess.check_call("systemctl start snap.microk8s.daemon-apiserver.service".split())

    waits = 10  # type: int
    print("Waiting for node to start.", end=" ", flush=True)
    time.sleep(10)
    while waits > 0:
        try:
            subprocess.check_output("{}/microk8s-kubectl.wrapper get service/kubernetes".format(snap_path).split())
            subprocess.check_output("{}/microk8s-kubectl.wrapper apply -f {}/args/cni-network/cilium.yaml"
                                  .format(snap_path, snapdata_path).split())
            break
        except subprocess.CalledProcessError:
            print(".", end=" ", flush=True)
            time.sleep(5)
            waits -= 1
    print(" ")
    restart_all_services()


def get_token(name: str, tokens_file: str = "known_tokens.csv") -> Optional[str]:
    """
    Get token from known_tokens file

    :param name: the name of the node
    :param tokens_file: the file where the tokens should go
    :returns: the token or None(if name doesn't exist)
    """
    file = "{}/credentials/{}".format(snapdata_path, tokens_file)  # type: str
    with open(file) as fp:
        for line in fp:
            if name in line:
                parts = line.split(',')
                return parts[0].rstrip()
    return None


def update_dqlite(cluster_cert: str, cluster_key: str, voters: str, host) -> None:
    """
    Configure the dqlite cluster

    :param cluster_cert: the dqlite cluster cert
    :param cluster_key: the dqlite cluster key
    :param voters: the dqlite voters
    :param host: the hostname others see of this node
    """
    subprocess.check_call("systemctl stop snap.microk8s.daemon-apiserver.service".split())
    time.sleep(10)
    shutil.rmtree(cluster_backup_dir, ignore_errors=True)
    shutil.move(cluster_dir, cluster_backup_dir)
    os.mkdir(cluster_dir)
    store_cluster_certs(cluster_cert, cluster_key)
    with open("{}/info.yaml".format(cluster_backup_dir)) as f:
        data = yaml.load(f, Loader=yaml.FullLoader)

    # TODO make port configurable
    init_data = {'Cluster': voters, 'Address': "{}:19001".format(host)}
    with open("{}/init.yaml".format(cluster_dir), 'w') as f:
        yaml.dump(init_data, f)

    subprocess.check_call("systemctl start snap.microk8s.daemon-apiserver.service".split())

    waits = 10
    print("Waiting for node to join the cluster.", end=" ", flush=True)
    while waits > 0:
        try:
            out = subprocess.check_output("curl https://{}/cluster/ --cacert {} --key {} --cert {} -k -s"
                                    .format(data['Address'], cluster_cert_file, cluster_key_file,
                                            cluster_cert_file).split());
            if data['Address'] in out.decode():
                break
            else:
                print(".", end=" ", flush=True)
                time.sleep(5)
                waits -= 1

        except subprocess.CalledProcessError:
            print("..", end=" ", flush=True)
            time.sleep(5)
            waits -= 1
    print(" ")
    restart_all_services()


def restart_all_services() -> None:
    """
    Restart all services
    """
    subprocess.check_call("{}/microk8s-stop.wrapper".format(snap_path).split())
    waits = 10  # type: int
    while waits > 0:
        try:
            subprocess.check_call("{}/microk8s-start.wrapper".format(snap_path).split())
            break
        except subprocess.CalledProcessError:
            time.sleep(5)
            waits -= 1


if __name__ == "__main__":
    try:
        # params: Tuple[List[Tuple[str, str]], List[str]]
        params = getopt.gnu_getopt(sys.argv[1:], "h", ["help"])
        opts = params[0]  # type: List[Tuple[str, str]]
        args = params[1]  # type: List[str]
    except getopt.GetoptError as err:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit(1)
        else:
            print("Unhandled option")
            sys.exit(1)

    if args[0] == "reset":
        reset_current_installation()
    else:
        if len(args) <= 0:
            print("Please provide a connection string.")
            usage()
            sys.exit(4)

        connection_parts = args[0].split("/")  # type: List[str]
        token = connection_parts[1]  # type: str
        master_ep = connection_parts[0].split(":")  # type: List[str]
        master_ip = master_ep[0]  # type: str
        master_port = master_ep[1]  # type: str
        info = get_connection_info(master_ip, master_port, token)  # type: Dict[str, str]

        if "cluster_key" not in info:
            print("The cluster you are attempting to join is incompatible with the current MicroK8s instance.")
            print("Please, either reinstall the node from a pre v1.18 track with "
                  "(sudo snap install microk8s --classic --channel=1.17/stable) "
                  "or update the cluster to a version newer than v1.17.")
            sys.exit(5)

        hostname_override = info['hostname_override']

        store_cert("ca.crt", info["ca"])
        store_cert("ca.key", info["ca_key"])
        store_cert("server.crt", info["server_cert"])
        store_cert("server.key", info["server_cert_key"])
        store_cert("serviceaccount.key", info["service_account_key"])
        store_cert("front-proxy-client.crt", info["proxy_cert"])
        store_cert("front-proxy-client.key", info["proxy_cert_key"])
        # triplets of [username in known_tokens.csv, username in kubeconfig, kubeconfig filename name]
        for component in [("kube-proxy", "kubeproxy", "proxy.config"),
                          ("kubelet", "kubelet", "kubelet.config"),
                          ("kube-controller-manager", "controller", "controller.config"),
                          ("kube-scheduler", "scheduler", "scheduler.config")]:
            component_token = get_token(component[0])  # type: Optional[str]
            if not component_token:
                print("Error, could not locate {} token. Joining cluster failed.".format(component[0]))
                exit(3)
            assert token is not None
            # TODO make this configurable
            create_kubeconfig(component_token, info["ca"], "127.0.0.1", "16443", component[2], component[1])
        create_admin_kubeconfig(info["ca"])
        store_base_kubelet_args(info["kubelet_args"])
        store_callback_token(info["callback_token"])

        update_dqlite(info["cluster_cert"], info["cluster_key"], info["voters"], hostname_override)

    sys.exit(0)
