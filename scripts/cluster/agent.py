#!flask/bin/python
import getopt
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from typing import Optional, Tuple, List

import yaml

from .common.utils import try_set_file_permissions, get_callback_token  # type: ignore

from flask import Flask, jsonify, request, Response, wrappers


app = Flask(__name__)
CLUSTER_API = "cluster/api/v1.0"  # type: str
CLUSTER_API_V2 = "cluster/api/v2.0"  # type: str
snapdata_path = os.environ.get('SNAP_DATA')  # type:  Optional[str]
snap_path = os.environ.get('SNAP')  # type:  Optional[str]
cluster_tokens_file = "{}/credentials/cluster-tokens.txt".format(snapdata_path)  # type: str
callback_token_file = "{}/credentials/callback-token.txt".format(snapdata_path)  # type: str
default_port = "25000"  # type: str
default_listen_interface = "0.0.0.0"  # type: str


@app.route('/{}/sign-cert'.format(CLUSTER_API), methods=['POST'])
def sign_cert_v1() -> wrappers.Response:
    """
    Version 1 of web call to sign a certificate
    Not implemented in this version of MicroK8s.
    Available in pre-1.18 versions.
    """
    error_msg = {"error": "Not possible to sign certs. Try a pre-1.18 version."}
    return Response(json.dumps(error_msg), mimetype='application/json', status=501)


@app.route('/{}/join'.format(CLUSTER_API), methods=['POST'])
def join_node_v1() -> wrappers.Response:
    """
    Version 1 of web call to join a node to the cluster.
    Not implemented in this version of MicroK8s.
    Available in pre-1.18 versions.
    """
    error_msg = {"error": "Not possible to join cluster. Try a pre-1.18 version."}
    return Response(json.dumps(error_msg), mimetype='application/json', status=501)


def get_service_name(service: str) -> str:
    """
    Returns the service name from its configuration file name.

    :param service: the name of the service configuration file
    :returns: the service name
    """
    if service in ["kube-proxy", "kube-apiserver", "kube-scheduler", "kube-controller-manager"]:
        return service[len("kube-"):]
    else:
        return service


def update_service_argument(service: str, key: str, val: Optional[str]) -> None:
    """
    Adds an argument to the arguments file of the service.

    :param service: the service
    :param key: the argument to add
    :param val: the value for the argument
    """

    args_file = "{}/args/{}".format(snapdata_path, service)  # type:  str
    args_file_tmp = "{}/args/{}.tmp".format(snapdata_path, service)  # type:  str
    found = False  # type:  bool
    with open(args_file_tmp, "w+") as bfp:
        with open(args_file, "r+") as fp:
            for _, line in enumerate(fp):
                if line.startswith(key):
                    if val is not None:
                        bfp.write("{}={}\n".format(key, val))
                    found = True
                else:
                    bfp.write("{}\n".format(line.rstrip()))
        if not found and val is not None:
            bfp.write("{}={}\n".format(key, val))

    try_set_file_permissions(args_file_tmp)
    shutil.move(args_file_tmp, args_file)


def remove_token_from_file(token: str, file: str) -> None:
    """
    Remove a token from the valid tokens set

    :param token: the token to be removed
    :param file: the file to be removed from
    """
    backup_file = "{}.backup".format(file)  # type:  str
    # That is a critical section. We need to protect it.
    # We are safe for now because flask serves one request at a time.
    with open(backup_file, 'w') as back_fp:
        with open(file, 'r') as fp:
            for _, line in enumerate(fp):
                if line.strip() == token:
                    continue
                back_fp.write("{}".format(line))

    shutil.copyfile(backup_file, file)


def get_cert(certificate: str) -> str:
    """
    Return the data of the certificate

    :returns: the certificate file contents
    """
    cert_file = "{}/certs/{}".format(snapdata_path, certificate)  # type: str
    with open(cert_file) as fp:
        cert = fp.read()  # type: str
    return cert


def get_cluster_certs() -> Tuple[str, str]:
    """
    Return the cluster certificates

    :returns: the cluster certificate files
    """
    file = "{}/var/kubernetes/backend/cluster.crt".format(snapdata_path)  # type:  str
    with open(file) as fp:
        cluster_cert = fp.read()
    file = "{}/var/kubernetes/backend/cluster.key".format(snapdata_path)
    with open(file) as fp:
        cluster_key = fp.read()

    return cluster_cert, cluster_key


def get_arg(key: str, file: str) -> Optional[str]:
    """
    Get an argument from an arguments file

    :param key: the argument we look for
    :param file: the arguments file to search in
    :returns: the value of the argument or None(if the key doesn't exist)
    """
    filename = "{}/args/{}".format(snapdata_path, file)  # type:  str
    with open(filename) as fp:
        for _, line in enumerate(fp):
            if line.startswith(key):
                args = line.split(' ')  # type: List[str]
                args = args[-1].split('=')
                return args[-1].rstrip()
    return None


def is_valid(token_line: str, token_type: str = cluster_tokens_file) -> bool:
    """
    Check whether a token is valid

    :param token: token to be checked
    :param token_type: the type of token (bootstrap or signature)
    :returns: True for a valid token, False otherwise
    """
    token = token_line.strip()
    # Ensure token is not empty
    if not token:
        return False

    with open(token_type) as fp:
        for _, line in enumerate(fp):
            if token == line.strip():
                return True
    return False


def read_kubelet_args_file(node: Optional[str] = None) -> Optional[str]:
    """
    Return the contents of the kubelet arguments file
    
    :param node: node to add a host override (defaults to None)
    :returns: the kubelet args file
    """
    filename = "{}/args/kubelet".format(snapdata_path)
    with open(filename) as fp:
        args = fp.read()
        if node:
            args = "{}--hostname-override {}".format(args, node)
        return args


def get_node_ep(hostname: str, remote_addr: str) -> str:
    """
    Return the endpoint to be used for the node based by trying to resolve the hostname provided
    
    :param hostname: the provided hostname
    :param remote_addr: the address the request came from
    :returns: the node's location
    """
    try:
        socket.gethostbyname(hostname)
        return hostname
    except socket.gaierror:
        return remote_addr
    return remote_addr


def get_dqlite_voters() -> List[str]:
    """
    Get the voting members of the dqlite cluster

    :param : the list with the voting members
    """
    snapdata_path = "/var/snap/microk8s/current"  # type:  str
    cluster_dir = "{}/var/kubernetes/backend".format(snapdata_path)  # type:  str
    cluster_cert_file = "{}/cluster.crt".format(cluster_dir)  # type:  str
    cluster_key_file = "{}/cluster.key".format(cluster_dir)  # type:  str

    waits = 10  # type:  int
    print("Waiting for access to cluster.", end=" ", flush=True)
    while waits > 0:
        try:
            with open("{}/info.yaml".format(cluster_dir)) as f:
                data = yaml.load(f, Loader=yaml.FullLoader)
                out = subprocess.check_output("curl https://{}/cluster --cacert {} --key {} --cert {} -k -s"
                                              .format(data['Address'], cluster_cert_file,
                                                      cluster_key_file, cluster_cert_file).split())
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
    if waits == 0:
        raise Exception("Could not get cluster info")

    nodes = yaml.safe_load(out)
    voters = []  # type: List[str]
    for n in nodes:
        if n["Role"] == 0:
            voters.append(n["Address"])
    return voters


def update_dqlite_ip(host: str) -> None:
    """
    Update dqlite so it listens on the default interface and not on localhost

    :param : the host others see for this node
    """
    subprocess.check_call("systemctl stop snap.microk8s.daemon-apiserver.service".split())
    time.sleep(10)

    cluster_dir = "{}/var/kubernetes/backend".format(snapdata_path)
    # TODO make the port configurable
    update_data = {'Address': "{}:19001".format(host)}
    with open("{}/update.yaml".format(cluster_dir), 'w') as f:
        yaml.dump(update_data, f)
    subprocess.check_call("systemctl start snap.microk8s.daemon-apiserver.service".split())


@app.route('/{}/join'.format(CLUSTER_API_V2), methods=['POST'])
def join_node() -> wrappers.Response:
    """
    Web call to join a node to the cluster
    """
    if request.headers['Content-Type'] == 'application/json':
        token = request.json['token']  # type: str
        hostname = request.json['hostname']  # type: str
        port = request.json['port']  # type: str
    else:
        token = request.form['token']
        hostname = request.form['hostname']
        port = request.form['port']

    if not is_valid(token):
        error_msg = {"error": "Invalid token"}
        return Response(json.dumps(error_msg), mimetype='application/json', status=500)

    voters = get_dqlite_voters()  # type: List[str]
    # Check if we need to set dqlite with external IP
    if len(voters) == 1 and voters[0].startswith("127.0.0.1"):
        update_dqlite_ip(request.host.split(":")[0])
        voters = get_dqlite_voters()
    callback_token = get_callback_token()  # type: str
    remove_token_from_file(token, cluster_tokens_file)
    node_addr = get_node_ep(hostname, request.remote_addr)  # type: str
    api_port = get_arg('--secure-port', 'kube-apiserver')  # type: Optional[str]
    kubelet_args = read_kubelet_args_file()  # type: Optional[str]
    cluster_cert, cluster_key = get_cluster_certs()

    return jsonify(ca=get_cert("ca.crt"),
                   ca_key=get_cert("ca.key"),
                   server_cert=get_cert("server.crt"),
                   server_cert_key=get_cert("server.key"),
                   service_account_key=get_cert("serviceaccount.key"),
                   proxy_cert=get_cert("front-proxy-client.crt"),
                   proxy_cert_key=get_cert("front-proxy-client.key"),
                   cluster_cert=cluster_cert,
                   cluster_key=cluster_key,
                   voters=voters,
                   callback_token=callback_token,
                   apiport=api_port,
                   kubelet_args=kubelet_args,
                   hostname_override=node_addr)


@app.route('/{}/configure'.format(CLUSTER_API), methods=['POST'])
def configure() -> wrappers.Response:
    """
    Web call to configure the node
    """
    if request.headers['Content-Type'] == 'application/json':
        callback_token = request.json['callback']  # type: str
        configuration = request.json
    else:
        callback_token = request.form['callback']
        configuration = json.loads(request.form['configuration'])

    callback_token = callback_token.strip()
    if not is_valid(callback_token, callback_token_file):
        error_msg={"error": "Invalid token"}
        return Response(json.dumps(error_msg), mimetype='application/json', status=500)

    # We expect something like this:
    '''
    {
      "callback": "xyztoken"
      "service":
      [
        {
          "name": "kubelet",
          "arguments_remove":
          [
            "myoldarg"
          ],
          "arguments_update":
          [
            {"myarg": "myvalue"},
            {"myarg2": "myvalue2"},
            {"myarg3": "myvalue3"}
          ],
          "restart": False
        },
        {
          "name": "kube-proxy",
          "restart": True
        }
      ],
      "addon":
      [
        {
          "name": "gpu",
          "enable": True
        },
        {
          "name": "gpu",
          "disable": True
        }
      ]
    }
    '''

    if "service" in configuration:
        for service in configuration["service"]:
            print("{}".format(service["name"]))
            if "arguments_update" in service:
                print("Updating arguments")
                for argument in service["arguments_update"]:
                    for key, val in argument.items():
                        print("{} is {}".format(key, val))
                        update_service_argument(service["name"], key, val)
            if "arguments_remove" in service:
                print("Removing arguments")
                for argument in service["arguments_remove"]:
                    print("{}".format(argument))
                    update_service_argument(service["name"], argument, None)
            if "restart" in service and service["restart"]:
                service_name = get_service_name(service["name"])
                print("restarting {}".format(service["name"]))
                subprocess.check_call("systemctl restart snap.microk8s.daemon-{}.service".format(service_name).split())

    if "addon" in configuration:
        for addon in configuration["addon"]:
            print("{}".format(addon["name"]))
            if "enable" in addon and addon["enable"]:
                print("Enabling {}".format(addon["name"]))
                subprocess.check_call("{}/microk8s-enable.wrapper {}".format(snap_path, addon["name"]).split())
            if "disable" in addon and addon["disable"]:
                print("Disabling {}".format(addon["name"]))
                subprocess.check_call("{}/microk8s-disable.wrapper {}".format(snap_path, addon["name"]).split())

    resp_date = {"result": "ok"}
    resp = Response(json.dumps(resp_date), status=200, mimetype='application/json')
    return resp


def usage() -> None:
    print("Agent responsible for setting up a cluster. Arguments:")
    print("-l, --listen:   interfaces to listen to (defaults to {})".format(default_listen_interface))
    print("-p, --port:     port to listen to (default {})".format(default_port))


if __name__ == '__main__':
    server_cert = "{SNAP_DATA}/certs/server.crt".format(SNAP_DATA=snapdata_path)  # type: str
    server_key = "{SNAP_DATA}/certs/server.key".format(SNAP_DATA=snapdata_path)  # type: str
    try:
        # params: Tuple[List[Tuple[str, str]], List[str]]
        params = getopt.gnu_getopt(sys.argv[1:], "hl:p:", ["help", "listen=", "port="])
        opts = params[0]  # type: List[Tuple[str, str]]
        args = params[1]  # type: List[str]
    except getopt.GetoptError as err:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
    port = default_port  # type: str
    listen = default_listen_interface  # type: str
    for o, a in opts:
        if o in ("-l", "--listen"):
            listen = a
        if o in ("-p", "--port"):
            port = a
        elif o in ("-h", "--help"):
            usage()
            sys.exit(1)
        else:
            assert False, "unhandled option"

    app.run(host=listen, port=port, ssl_context=(server_cert, server_key))
