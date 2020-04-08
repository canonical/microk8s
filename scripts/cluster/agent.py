#!flask/bin/python
import getopt
import json
import yaml
import os
import random
import shutil
import socket
import string
import subprocess
import sys

from common.utils import try_set_file_permissions

from flask import Flask, jsonify, request, abort, Response
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
CLUSTER_API="cluster/api/v1.0"
snapdata_path = os.environ.get('SNAP_DATA')
snap_path = os.environ.get('SNAP')
cluster_tokens_file = "{}/credentials/cluster-tokens.txt".format(snapdata_path)
callback_tokens_file = "{}/credentials/callback-tokens.txt".format(snapdata_path)
callback_token_file = "{}/credentials/callback-token.txt".format(snapdata_path)
certs_request_tokens_file = "{}/credentials/certs-request-tokens.txt".format(snapdata_path)
enable_extended_api_file = "{}/args/enable-extended-api".format(snapdata_path)
default_port = 25000
default_listen_interface = "0.0.0.0"
ext_api_error_message = "{} request is not allowed if Extended API is not enabled. You can enable it by creating " \
                        "a file with the name 'enable-extended-api' under '" + enable_extended_api_file + "', " \
                        "HAVING THE SAME TOKEN VALUE with '" + callback_token_file + "'"

# -- swagger specific --
SWAGGER_URL = '/swagger'
API_URL = '/swagger.json'
SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "MicroK8s REST API"
    }
)
app.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)
# -- end swagger specific --

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
    sign_cmd = "openssl x509 -sha256 -req -in {csr} -CA {SNAP_DATA}/certs/ca.crt -CAkey" \
               " {SNAP_DATA}/certs/ca.key -CAcreateserial -out {SNAP_DATA}/certs/server.{token}.crt" \
               " -days 365".format(csr=req_file, SNAP_DATA=snapdata_path, token=token)

    with open(req_file, 'w') as fp:
        fp.write(cert_request)
    subprocess.check_call(sign_cmd.split())
    with open("{SNAP_DATA}/certs/server.{token}.crt".format(SNAP_DATA=snapdata_path, token=token)) as fp:
        cert = fp.read()
    return cert


def add_token_to_certs_request(token):
    """
    Add a token to the file holding the nodes we expect a certificate request from
    
    :param token: the token
    """
    with open(certs_request_tokens_file, "a+") as fp:
        fp.write("{}\n".format(token))


def remove_token_from_file(token, file):
    """
    Remove a token from the valid tokens set
    
    :param token: the token to be removed
    :param file: the file to be removed from
    """
    backup_file = "{}.backup".format(file)
    # That is a critical section. We need to protect it.
    # We are safe for now because flask serves one request at a time.
    with open(backup_file, 'w') as back_fp:
        with open(file, 'r') as fp:
            for _, line in enumerate(fp):
                if line.strip() == token:
                    continue
                back_fp.write("{}".format(line))

    shutil.copyfile(backup_file, file)


def get_token(name):
    """
    Get token from known_tokens file

    :param name: the name of the node
    :returns: the token or None(if name doesn't exist)
    """
    file = "{}/credentials/known_tokens.csv".format(snapdata_path)
    with open(file) as fp:
        line = fp.readline()
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
            if token == line.strip():
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
def join_node():
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

    if not is_valid(token):
        error_msg={"error": "Invalid token"}
        return Response(json.dumps(error_msg), mimetype='application/json', status=500)

    add_token_to_certs_request(token)
    remove_token_from_file(token, cluster_tokens_file)

    node_addr = get_node_ep(hostname, request.remote_addr)
    node_ep = "{}:{}".format(node_addr, port)
    store_callback_token(node_ep, callback_token)

    ca = getCA()
    etcd_ep = get_arg('--listen-client-urls', 'etcd')
    api_port = get_arg('--secure-port', 'kube-apiserver')
    proxy_token = get_token('kube-proxy')
    kubelet_token = add_kubelet_token(node_addr)
    subprocess.check_call("systemctl restart snap.microk8s.daemon-apiserver.service".split())
    if node_addr != hostname:
        kubelet_args = read_kubelet_args_file(node_addr)
    else:
        kubelet_args = read_kubelet_args_file()

    return jsonify(ca=ca,
                   etcd=etcd_ep,
                   kubeproxy=proxy_token,
                   apiport=api_port,
                   kubelet=kubelet_token,
                   kubelet_args=kubelet_args,
                   hostname_override=node_addr)


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
        error_msg={"error": "Invalid token"}
        return Response(json.dumps(error_msg), mimetype='application/json', status=500)

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
        error_msg={"error": "Invalid token"}
        return Response(json.dumps(error_msg), mimetype='application/json', status=500)

    # We expect something like this:
    '''
    {
      "callback": "xyztoken",
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


@app.route('/{}/version'.format(CLUSTER_API), methods=['POST', 'GET'])
def version():
    """
    Web call to get microk8s version installed
    """
    if request.method.upper() == 'GET' and not is_extended_api_enabled():
        error_msg = {"error": ext_api_error_message.format('GET')}
        return Response(json.dumps(error_msg), mimetype='application/json', status=400)
    if request.method.upper() == 'POST':
        v = callback_token_validation(request)
        if not v["valid"]: return v["response"]
    output = subprocess.check_output("snap info microk8s".split())

    json_output = yaml.full_load(output)
    return json_output["installed"].split(' ')[0]


@app.route('/{}/services'.format(CLUSTER_API), methods=['POST'])
def services():
    """
    Web call to get all microk8s services
    Output sample:
      microk8s.daemon-apiserver
      microk8s.daemon-apiserver-kicker
      microk8s.daemon-cluster-agent
      microk8s.daemon-containerd
      microk8s.daemon-controller-manager
      microk8s.daemon-etcd
      microk8s.daemon-flanneld
      microk8s.daemon-kubelet
      microk8s.daemon-proxy
      microk8s.daemon-scheduler
    """
    v = callback_token_validation(request)
    if not v["valid"]: return v["response"]
    output = subprocess.check_output("snap info microk8s".split())
    json_output = yaml.full_load(output)
    return app.response_class(response=json.dumps(json_output["services"], sort_keys=False, indent=4), status=200, mimetype='application/json')


@app.route('/{}/service/restart'.format(CLUSTER_API), methods=['POST'])
def service_restart():
    """
    Web call to restart a service
    :request_param service: the name of the service
    """
    v = callback_token_validation(request)
    if not v["valid"]: return v["response"]
    if "service" not in request.json or len(request.json["service"].strip()) == 0:
        error_msg = {"error": "Empty service provided"}
        return Response(json.dumps(error_msg), mimetype='application/json', status=400)
    output = subprocess.check_output("systemctl restart snap.{}.service".format(request.json["service"]).split())
    return output


@app.route('/{}/service/start'.format(CLUSTER_API), methods=['POST'])
def service_start():
    """
    Web call to start a service
    :request_param service: the name of the service
    """
    v = callback_token_validation(request)
    if not v["valid"]: return v["response"]
    if "service" not in request.json or len(request.json["service"].strip()) == 0:
        error_msg = {"error": "Empty service provided"}
        return Response(json.dumps(error_msg), mimetype='application/json', status=400)
    output = subprocess.check_output("systemctl start snap.{}.service".format(request.json["service"]).split())
    return output


@app.route('/{}/service/stop'.format(CLUSTER_API), methods=['POST'])
def service_stop():
    """
    Web call to start a service
    :request_param service: the name of the service
    """
    v = callback_token_validation(request)
    if not v["valid"]: return v["response"]
    if "service" not in request.json or len(request.json["service"].strip()) == 0:
        error_msg = {"error": "Empty service provided"}
        return Response(json.dumps(error_msg), mimetype='application/json', status=400)
    output = subprocess.check_output("systemctl stop snap.{}.service".format(request.json["service"]).split())
    return output


@app.route('/{}/service/enable'.format(CLUSTER_API), methods=['POST'])
def service_enable():
    """
    Web call to enable a service
    :request_param service: the name of the service
    """
    v = callback_token_validation(request)
    if not v["valid"]: return v["response"]
    if "service" not in request.json or len(request.json["service"].strip()) == 0:
        error_msg = {"error": "Empty service provided"}
        return Response(json.dumps(error_msg), mimetype='application/json', status=400)
    output = subprocess.check_output("systemctl enable snap.{}.service".format(request.json["service"]).split())
    return output


@app.route('/{}/service/disable'.format(CLUSTER_API), methods=['POST'])
def service_disable():
    """
    Web call to enable a service
    :request_param service: the name of the service
    """
    v = callback_token_validation(request)
    if not v["valid"]: return v["response"]
    if "service" not in request.json or len(request.json["service"].strip()) == 0:
        error_msg = {"error": "Empty service provided"}
        return Response(json.dumps(error_msg), mimetype='application/json', status=400)
    output = subprocess.check_output("systemctl disable snap.{}.service".format(request.json["service"]).split())
    return output


@app.route('/{}/service/logs'.format(CLUSTER_API), methods=['POST'])
def service_logs():
    """
    Web call to the logs of a service
    :request_param service: the name of the service
    :request_param lines: total lines | if omitted default value 10 will be used
    """
    lines = 10
    v = callback_token_validation(request)
    if not v["valid"]: return v["response"]
    if "service" not in request.json or len(request.json["service"].strip()) == 0:
        error_msg = {"error": "Empty service provided"}
        return Response(json.dumps(error_msg), mimetype='application/json', status=400)
    if "lines" in request.json:
        lines = request.json["lines"]
    # more info on logs could be obtained by using: --output=json-pretty
    output = subprocess.check_output("journalctl --lines={} --unit=snap.{}.service --no-pager".format(lines, request.json["service"]).split())
    return output


@app.route('/{}/addon/enable'.format(CLUSTER_API), methods=['POST'])
def enable():
    """
    Web call to microk8s.enable <addon>
    :request_param addon: the name of the addon
    """
    v = callback_token_validation(request)
    if not v["valid"]: return v["response"]
    if "addon" not in request.json or len(request.json["addon"].strip()) == 0:
        error_msg = {"error": "Empty addon provided"}
        return Response(json.dumps(error_msg), mimetype='application/json', status=400)
    output = subprocess.check_output("{}/microk8s-enable.wrapper {}".format(snap_path, request.json["addon"]).split())
    return output


@app.route('/{}/addon/disable'.format(CLUSTER_API), methods=['POST'])
def disable():
    """
    Web call to microk8s.disable <addon>
    :request_param addon: the name of the addon
    """
    v = callback_token_validation(request)
    if not v["valid"]: return v["response"]
    if "addon" not in request.json or len(request.json["addon"].strip()) == 0:
        error_msg = {"error": "Empty addon provided"}
        return Response(json.dumps(error_msg), mimetype='application/json', status=400)
    output = subprocess.check_output("{}/microk8s-disable.wrapper {}".format(snap_path, request.json["addon"]).split())
    return output


@app.route('/{}/start'.format(CLUSTER_API), methods=['POST'])
def start():
    """
    Web call for microk8s.start
    """
    v = callback_token_validation(request)
    if not v["valid"]: return v["response"]
    output = subprocess.check_output("{}/microk8s-start.wrapper".format(snap_path).split())
    return output


@app.route('/{}/stop'.format(CLUSTER_API), methods=['POST'])
def stop():
    """
    Web call for microk8s.stop
    """
    v = callback_token_validation(request)
    if not v["valid"]: return v["response"]
    output = subprocess.check_output("{}/microk8s-stop.wrapper".format(snap_path).split())
    return output


@app.route('/{}/overview'.format(CLUSTER_API), methods=['POST'])
def overview():
    """
    Web call to get the microk8s.kubectl get all --all-namespaces
    """
    v = callback_token_validation(request)
    if not v["valid"]: return v["response"]
    output = subprocess.check_output("{}/microk8s-kubectl.wrapper get all --all-namespaces".format(snap_path).split())
    return output


@app.route('/{}/status'.format(CLUSTER_API), methods=['POST', 'GET'])
def status():
    """
    Web call to get the microk8s status
    """
    cmd = "{}/microk8s-status.wrapper --format yaml --timeout 60".format(snap_path)
    if request.method.upper() == 'GET' and not is_extended_api_enabled():
        error_msg = {"error": ext_api_error_message.format('GET')}
        return Response(json.dumps(error_msg), mimetype='application/json', status=400)
    if request.method.upper() == 'POST':
        v = callback_token_validation(request)
        if not v["valid"]: return v["response"]
        if "addon" in request.json:
            cmd = "{}/microk8s-status.wrapper -a {}".format(snap_path, request.json["addon"])

    output = subprocess.check_output(cmd.split())

    if request.json and "addon" in request.json:
        json_output = {"addon": request.json["addon"], "status": output.decode().strip('\n')}
    else:
        json_output = yaml.full_load(output)

    return app.response_class(response=json.dumps(json_output, sort_keys=False, indent=4), status=200, mimetype='application/json')


@app.route('/{}/config'.format(CLUSTER_API), methods=['POST'])
def config():
    """
    Web call to get the microk8s config
    """
    cmd = "{}/microk8s-config.wrapper".format(snap_path)
    if not is_extended_api_enabled():
        error_msg = {"error": ext_api_error_message.format('This')}
        return Response(json.dumps(error_msg), mimetype='application/json', status=400)

    v = callback_token_validation(request)
    if not v["valid"]: return v["response"]

    output = subprocess.check_output(cmd.split())
    json_output = yaml.full_load(output)

    return app.response_class(response=json.dumps(json_output, sort_keys=False, indent=4), status=200, mimetype='application/json')


@app.route('/swagger.json', methods=['GET'])
def swagger_json():
    with open(os.path.join(os.path.dirname(__file__), "static/swagger.yaml")) as f:
        content = f.read()
    return app.response_class(response=json.dumps(yaml.full_load(content), sort_keys=False, indent=4), status=200, mimetype='application/json')


def callback_token_validation(request):
    if request.headers['Content-Type'] == 'application/json':
        callback_token = request.json['callback']
    else:
        callback_token = request.form['callback']
    valid = is_valid(callback_token, callback_token_file)
    resp = None
    if not valid:
        error_msg = {"error": "Invalid token"}
        resp = Response(json.dumps(error_msg), mimetype='application/json', status=500)
    return {"valid": valid, "response": resp}


def is_extended_api_enabled():
    """
    Check if user has created enable_extended_api, having the same token value with credentials/callback-token.txt
    """
    if not os.path.exists(enable_extended_api_file):
        return False

    with open(callback_token_file, 'r') as file:
        cb_token_file_value = file.read().replace('\n', '')
    with open(enable_extended_api_file, 'r') as file:
        enable_extended_api_file_value = file.read().replace('\n', '')

    return cb_token_file_value == enable_extended_api_file_value


def usage():
    print("Agent responsible for setting up a cluster. Arguments:")
    print("-l, --listen:   interfaces to listen to (defaults to {})".format(default_listen_interface))
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
