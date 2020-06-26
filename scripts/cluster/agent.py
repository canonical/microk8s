#!flask/bin/python
import getopt
import json
import os
import random
import shutil
import socket
import string
import subprocess
import sys
import time

import yaml

from .common.utils import (
    try_set_file_permissions,
    remove_expired_token_from_file,
    is_node_running_dqlite,
    get_callback_token,
    remove_token_from_file,
    is_token_expired,
    get_dqlite_port,
    get_cluster_agent_port,
)

from flask import Flask, jsonify, request, abort, Response

app = Flask(__name__)
CLUSTER_API = "cluster/api/v1.0"
CLUSTER_API_V2 = "cluster/api/v2.0"
snapdata_path = os.environ.get('SNAP_DATA')
snap_path = os.environ.get('SNAP')
cluster_tokens_file = "{}/credentials/cluster-tokens.txt".format(snapdata_path)
callback_token_file = "{}/credentials/callback-token.txt".format(snapdata_path)
callback_tokens_file = "{}/credentials/callback-tokens.txt".format(snapdata_path)
certs_request_tokens_file = "{}/credentials/certs-request-tokens.txt".format(snapdata_path)
default_port = 25000
dqlite_default_port = 19001
default_listen_interface = "0.0.0.0"


def get_service_name(service):
    """
    Returns the service name from its configuration file name.

    :param service: the name of the service configuration file
    :returns: the service name
    """
    if service in ["kube-proxy", "kube-apiserver", "kube-scheduler", "kube-controller-manager"]:
        return service[len("kube-"), :]
    else:
        return service


def update_service_argument(service, key, val):
    """
    Adds an argument to the arguments file of the service.

    :param service: the service
    :param key: the argument to add
    :param val: the value for the argument
    """

    args_file = "{}/args/{}".format(snapdata_path, service)
    args_file_tmp = "{}/args/{}.tmp".format(snapdata_path, service)
    found = False
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


def store_callback_token(node, callback_token):
    """
    Store a callback token

    :param node: the node
    :param callback_token: the token
    """
    tmp_file = "{}.tmp".format(callback_tokens_file)
    if not os.path.isfile(callback_tokens_file):
        open(callback_tokens_file, 'a+')
        os.chmod(callback_tokens_file, 0o600)
    with open(tmp_file, "w") as backup_fp:
        os.chmod(tmp_file, 0o600)
        found = False
        with open(callback_tokens_file, 'r+') as callback_fp:
            for _, line in enumerate(callback_fp):
                if line.startswith(node):
                    backup_fp.write("{} {}\n".format(node, callback_token))
                    found = True
                else:
                    backup_fp.write(line)
        if not found:
            backup_fp.write("{} {}\n".format(node, callback_token))

    try_set_file_permissions(tmp_file)
    shutil.move(tmp_file, callback_tokens_file)


def sign_client_cert(cert_request, token):
    """
    Sign a certificate request
    
    :param cert_request: the request
    :param token: a token acting as a request uuid
    :returns: the certificate
    """
    req_file = "{}/certs/request.{}.csr".format(snapdata_path, token)
    sign_cmd = (
        "openssl x509 -sha256 -req -in {csr} -CA {SNAP_DATA}/certs/ca.crt -CAkey"
        " {SNAP_DATA}/certs/ca.key -CAcreateserial -out {SNAP_DATA}/certs/server.{token}.crt"
        " -days 365".format(csr=req_file, SNAP_DATA=snapdata_path, token=token)
    )

    with open(req_file, 'w') as fp:
        fp.write(cert_request)
    subprocess.check_call(sign_cmd.split())
    with open(
        "{SNAP_DATA}/certs/server.{token}.crt".format(SNAP_DATA=snapdata_path, token=token)
    ) as fp:
        cert = fp.read()
    return cert


def add_token_to_certs_request(token):
    """
    Add a token to the file holding the nodes we expect a certificate request from
    
    :param token: the token
    """
    with open(certs_request_tokens_file, "a+") as fp:
        fp.write("{}\n".format(token))


def get_token(name):
    """
    Get token from known_tokens file

    :param name: the name of the node
    :returns: the token or None(if name doesn't exist)
    """
    file = "{}/credentials/known_tokens.csv".format(snapdata_path)
    with open(file) as fp:
        for _, line in enumerate(fp):
            if name in line:
                parts = line.split(',')
                return parts[0].rstrip()
    return None


def add_kubelet_token(hostname):
    """
    Add a token for a node in the known tokens

    :param hostname: the name of the node
    :returns: the token added
    """
    file = "{}/credentials/known_tokens.csv".format(snapdata_path)
    old_token = get_token("system:node:{}".format(hostname))
    if old_token:
        return old_token.rstrip()

    alpha = string.ascii_letters + string.digits
    token = ''.join(random.SystemRandom().choice(alpha) for _ in range(32))
    uid = ''.join(random.SystemRandom().choice(string.digits) for _ in range(8))
    with open(file, 'a') as fp:
        # TODO double check this format. Why is userid unique?
        line = "{},system:node:{},kubelet-{},\"system:nodes\"".format(token, hostname, uid)
        fp.write(line + os.linesep)
    return token.rstrip()


def getCA():
    """
    Return the CA
    
    :returns: the CA file contents
    """
    ca_file = "{}/certs/ca.crt".format(snapdata_path)
    with open(ca_file) as fp:
        ca = fp.read()
    return ca


def get_arg(key, file):
    """
    Get an argument from an arguments file

    :param key: the argument we look for
    :param file: the arguments file to search in
    :returns: the value of the argument or None(if the key doesn't exist)
    """
    filename = "{}/args/{}".format(snapdata_path, file)
    with open(filename) as fp:
        for _, line in enumerate(fp):
            if line.startswith(key):
                args = line.split(' ')
                args = args[-1].split('=')
                return args[-1].rstrip()
    return None


def is_valid(token_line, token_type=cluster_tokens_file):
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
            token_in_file = line.strip()
            if "|" in line:
                if not is_token_expired(line):
                    token_in_file = line.strip().split('|')[0]
            if token == token_in_file:
                return True
    return False


def read_kubelet_args_file(node=None):
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


def get_node_ep(hostname, remote_addr):
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


@app.route('/{}/join'.format(CLUSTER_API), methods=['POST'])
def join_node_etcd():
    """
    Web call to join a node to the cluster
    """
    if request.headers['Content-Type'] == 'application/json':
        token = request.json['token']
        hostname = request.json['hostname']
        port = request.json['port']
        callback_token = request.json['callback']
    else:
        token = request.form['token']
        hostname = request.form['hostname']
        port = request.form['port']
        callback_token = request.form['callback']

    # Remove expired tokens
    remove_expired_token_from_file(cluster_tokens_file)

    if not is_valid(token):
        error_msg = {"error": "Invalid token"}
        return Response(json.dumps(error_msg), mimetype='application/json', status=500)

    if is_node_running_dqlite():
        msg = (
            "Failed to join the cluster. This is an HA dqlite cluster. \n"
            "Please, retry after enabling HA on this joining node with 'microk8s enable ha-cluster'."
        )
        error_msg = {"error": msg}
        return Response(json.dumps(error_msg), mimetype='application/json', status=501)

    add_token_to_certs_request(token)
    # remove token for backwards compatibility way of adding a node
    remove_token_from_file(token, cluster_tokens_file)

    node_addr = get_node_ep(hostname, request.remote_addr)
    node_ep = "{}:{}".format(node_addr, port)
    store_callback_token(node_ep, callback_token)

    ca = getCA()
    etcd_ep = get_arg('--listen-client-urls', 'etcd')
    api_port = get_arg('--secure-port', 'kube-apiserver')
    proxy_token = get_token('kube-proxy')
    kubelet_token = add_kubelet_token(node_addr)
    subprocess.check_call("snapctl restart microk8s.daemon-apiserver".split())
    if node_addr != hostname:
        kubelet_args = read_kubelet_args_file(node_addr)
    else:
        kubelet_args = read_kubelet_args_file()

    return jsonify(
        ca=ca,
        etcd=etcd_ep,
        kubeproxy=proxy_token,
        apiport=api_port,
        kubelet=kubelet_token,
        kubelet_args=kubelet_args,
        hostname_override=node_addr,
    )


@app.route('/{}/sign-cert'.format(CLUSTER_API), methods=['POST'])
def sign_cert():
    """
    Web call to sign a certificate
    """
    if request.headers['Content-Type'] == 'application/json':
        token = request.json['token']
        cert_request = request.json['request']
    else:
        token = request.form['token']
        cert_request = request.form['request']

    token = token.strip()
    if not is_valid(token, certs_request_tokens_file):
        error_msg = {"error": "Invalid token"}
        return Response(json.dumps(error_msg), mimetype='application/json', status=500)

    if is_node_running_dqlite():
        error_msg = {"error": "Not possible to join. This is an HA dqlite cluster."}
        return Response(json.dumps(error_msg), mimetype='application/json', status=501)

    remove_token_from_file(token, certs_request_tokens_file)
    signed_cert = sign_client_cert(cert_request, token)
    return jsonify(certificate=signed_cert)


@app.route('/{}/configure'.format(CLUSTER_API), methods=['POST'])
def configure():
    """
    Web call to configure the node
    """
    if request.headers['Content-Type'] == 'application/json':
        callback_token = request.json['callback']
        configuration = request.json
    else:
        callback_token = request.form['callback']
        configuration = json.loads(request.form['configuration'])

    callback_token = callback_token.strip()
    if not is_valid(callback_token, callback_token_file):
        error_msg = {"error": "Invalid token"}
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
                subprocess.check_call(
                    "snapctl restart microk8s.daemon-{}".format(service_name).split()
                )

    if "addon" in configuration:
        for addon in configuration["addon"]:
            print("{}".format(addon["name"]))
            if "enable" in addon and addon["enable"]:
                print("Enabling {}".format(addon["name"]))
                subprocess.check_call(
                    "{}/microk8s-enable.wrapper {}".format(snap_path, addon["name"]).split()
                )
            if "disable" in addon and addon["disable"]:
                print("Disabling {}".format(addon["name"]))
                subprocess.check_call(
                    "{}/microk8s-disable.wrapper {}".format(snap_path, addon["name"]).split()
                )

    resp_date = {"result": "ok"}
    resp = Response(json.dumps(resp_date), status=200, mimetype='application/json')
    return resp


def get_dqlite_voters():
    """
    Get the voting members of the dqlite cluster

    :param : the list with the voting members
    """
    snapdata_path = "/var/snap/microk8s/current"
    cluster_dir = "{}/var/kubernetes/backend".format(snapdata_path)

    waits = 10
    print("Waiting for access to cluster.", end=" ", flush=True)
    while waits > 0:
        try:
            with open("{}/info.yaml".format(cluster_dir)) as f:
                data = yaml.load(f, Loader=yaml.FullLoader)
                out = subprocess.check_output(
                    "{snappath}/bin/dqlite -s file://{dbdir}/cluster.yaml -c {dbdir}/cluster.crt "
                    "-k {dbdir}/cluster.key -f json k8s .cluster".format(
                        snappath=snap_path, dbdir=cluster_dir
                    ).split(),
                    timeout=4,
                )
                if data['Address'] in out.decode():
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
    if waits == 0:
        raise Exception("Could not get cluster info")

    nodes = json.loads(out.decode())
    voters = []
    for n in nodes:
        if n["Role"] == 0:
            voters.append(n["Address"])
    return voters


def update_dqlite_ip(host):
    """
    Update dqlite so it listens on the default interface and not on localhost

    :param : the host others see for this node
    """
    dqlite_port = get_dqlite_port()
    subprocess.check_call("snapctl stop microk8s.daemon-apiserver".split())
    time.sleep(10)

    cluster_dir = "{}/var/kubernetes/backend".format(snapdata_path)
    # TODO make the port configurable
    update_data = {'Address': "{}:{}".format(host, dqlite_port)}
    with open("{}/update.yaml".format(cluster_dir), 'w') as f:
        yaml.dump(update_data, f)
    subprocess.check_call("snapctl start microk8s.daemon-apiserver".split())
    time.sleep(10)
    attempts = 12
    while True:
        voters = get_dqlite_voters()
        if len(voters) > 0 and not voters[0].startswith("127.0.0.1"):
            break
        else:
            time.sleep(5)
            attempts -= 1
        if attempts <= 0:
            break


def get_cert(certificate):
    """
    Return the data of the certificate

    :returns: the certificate file contents
    """
    cert_file = "{}/certs/{}".format(snapdata_path, certificate)
    with open(cert_file) as fp:
        cert = fp.read()
    return cert


def get_cluster_certs():
    """
    Return the cluster certificates

    :returns: the cluster certificate files
    """
    file = "{}/var/kubernetes/backend/cluster.crt".format(snapdata_path)
    with open(file) as fp:
        cluster_cert = fp.read()
    file = "{}/var/kubernetes/backend/cluster.key".format(snapdata_path)
    with open(file) as fp:
        cluster_key = fp.read()

    return cluster_cert, cluster_key


@app.route('/{}/join'.format(CLUSTER_API_V2), methods=['POST'])
def join_node_dqlite():
    """
    Web call to join a node to the cluster
    """
    if request.headers['Content-Type'] == 'application/json':
        token = request.json['token']
        hostname = request.json['hostname']
        port = request.json['port']
    else:
        token = request.form['token']
        hostname = request.form['hostname']
        port = request.form['port']

    if not is_valid(token):
        error_msg = {"error": "Invalid token"}
        return Response(json.dumps(error_msg), mimetype='application/json', status=500)

    if not is_node_running_dqlite():
        error_msg = {"error": "Not possible to join. This is not an HA dqlite cluster."}
        return Response(json.dumps(error_msg), mimetype='application/json', status=501)

    agent_port = get_cluster_agent_port()
    if port != agent_port:
        error_msg = {
            "error": "The port of the cluster agent has to be set to {}.".format(agent_port)
        }
        return Response(json.dumps(error_msg), mimetype='application/json', status=502)

    voters = get_dqlite_voters()  # type: List[str]
    # Check if we need to set dqlite with external IP
    if len(voters) == 1 and voters[0].startswith("127.0.0.1"):
        update_dqlite_ip(request.host.split(":")[0])
        voters = get_dqlite_voters()
    callback_token = get_callback_token()
    remove_token_from_file(token, cluster_tokens_file)
    node_addr = request.remote_addr
    api_port = get_arg('--secure-port', 'kube-apiserver')
    kubelet_args = read_kubelet_args_file()
    cluster_cert, cluster_key = get_cluster_certs()

    return jsonify(
        ca=get_cert("ca.crt"),
        ca_key=get_cert("ca.key"),
        service_account_key=get_cert("serviceaccount.key"),
        cluster_cert=cluster_cert,
        cluster_key=cluster_key,
        voters=voters,
        callback_token=callback_token,
        apiport=api_port,
        kubelet_args=kubelet_args,
        hostname_override=node_addr,
        admin_token=get_token('admin'),
    )


@app.route('/{}/upgrade'.format(CLUSTER_API), methods=['POST'])
def upgrade():
    """
    Web call to upgrade the node
    """
    callback_token = request.json['callback']
    callback_token = callback_token.strip()
    if not is_valid(callback_token, callback_token_file):
        error_msg = {"error": "Invalid token"}
        return Response(json.dumps(error_msg), mimetype='application/json', status=500)

    upgrade_request = request.json["upgrade"]
    phase = request.json["phase"]

    # We expect something like this:
    '''
    {
      "callback": "xyztoken"
      "phase": "prepare", "commit" or "rollback"
      "upgrade": "XYZ-upgrade-name"
    }
    '''
    if phase == "prepare":
        upgrade_script = '{}/upgrade-scripts/{}/prepare-node.sh'.format(snap_path, upgrade_request)
        if not os.path.isfile(upgrade_script):
            print("Not ready to execute {}".format(upgrade_script))
            resp_data = {"result": "not ok"}
            resp = Response(json.dumps(resp_data), status=404, mimetype='application/json')
            return resp
        else:
            print("Executing {}".format(upgrade_script))
            subprocess.check_call(upgrade_script)
            resp_data = {"result": "ok"}
            resp = Response(json.dumps(resp_data), status=200, mimetype='application/json')
            return resp

    elif phase == "commit":
        upgrade_script = '{}/upgrade-scripts/{}/commit-node.sh'.format(snap_path, upgrade_request)
        print("Ready to execute {}".format(upgrade_script))
        print("Executing {}".format(upgrade_script))
        subprocess.check_call(upgrade_script)
        resp_data = {"result": "ok"}
        resp = Response(json.dumps(resp_data), status=200, mimetype='application/json')
        return resp

    elif phase == "rollback":
        upgrade_script = '{}/upgrade-scripts/{}/rollback-node.sh'.format(snap_path, upgrade_request)
        print("Ready to execute {}".format(upgrade_script))
        print("Executing {}".format(upgrade_script))
        subprocess.check_call(upgrade_script)
        resp_data = {"result": "ok"}
        resp = Response(json.dumps(resp_data), status=200, mimetype='application/json')
        return resp


def usage():
    print("Agent responsible for setting up a cluster. Arguments:")
    print(
        "-l, --listen:   interfaces to listen to (defaults to {})".format(default_listen_interface)
    )
    print("-p, --port:     port to listen to (default {})".format(default_port))


if __name__ == '__main__':
    server_cert = "{SNAP_DATA}/certs/server.crt".format(SNAP_DATA=snapdata_path)
    server_key = "{SNAP_DATA}/certs/server.key".format(SNAP_DATA=snapdata_path)
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "hl:p:", ["help", "listen=", "port="])
    except getopt.GetoptError as err:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
    port = default_port
    listen = default_listen_interface
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
