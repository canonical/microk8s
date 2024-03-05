import base64
import datetime
import ipaddress
import json
import os
import random
import re
import shutil
import socket
import string
import subprocess
import time
from pathlib import Path
from subprocess import CalledProcessError, check_output

import yaml

FINGERPRINT_MIN_LEN = 12
TOKEN_ΜΙΝ_LEN = 32


class InvalidConnectionError(Exception):
    pass


def is_strict():
    snap_yaml = snap() / "meta/snap.yaml"
    with open(snap_yaml) as f:
        snap_meta = yaml.safe_load(f)
    return snap_meta["confinement"] == "strict"


def get_group():
    return "snap_microk8s" if is_strict() else "microk8s"


def snap() -> Path:
    try:
        return Path(os.environ["SNAP"])
    except KeyError:
        return Path("/snap/microk8s/current")


def snap_data() -> Path:
    try:
        return Path(os.environ["SNAP_DATA"])
    except KeyError:
        return Path("/var/snap/microk8s/current")


def try_set_file_permissions(file):
    """
    Try setting the ownership group and permission of the file

    :param file: full path and filename
    """
    mode = 0o660
    group = get_group()

    if os.path.exists(snap_data() / "var" / "lock" / "cis-hardening"):
        group = "root"
        mode = 0o600

    os.chmod(file, mode)
    try:
        shutil.chown(file, group=group)
    except LookupError:
        # not setting the group means only the current user can access the file
        pass


def remove_expired_token_from_file(file):
    """
    Remove expired token from the valid tokens set

    :param file: the file to be removed from
    """
    backup_file = "{}.backup".format(file)
    # That is a critical section. We need to protect it.
    # We are safe for now because flask serves one request at a time.
    with open(backup_file, "w") as back_fp:
        with open(file, "r") as fp:
            for _, line in enumerate(fp):
                if is_token_expired(line):
                    continue
                back_fp.write("{}".format(line))

    try_set_file_permissions(backup_file)
    shutil.copyfile(backup_file, file)


def remove_token_from_file(token, file):
    """
    Remove a token from the valid tokens set

    :param token: the token to be removed
    :param file: the file to be removed from
    """
    backup_file = "{}.backup".format(file)
    # That is a critical section. We need to protect it.
    # We are safe for now because flask serves one request at a time.
    with open(backup_file, "w") as back_fp:
        with open(file, "r") as fp:
            for _, line in enumerate(fp):
                # Not considering cluster tokens with expiry in this method.
                if "|" not in line:
                    if line.strip() == token:
                        continue
                back_fp.write("{}".format(line))

    try_set_file_permissions(backup_file)
    shutil.copyfile(backup_file, file)


def is_token_expired(token_line):
    """
    Checks if the token in the file is expired, when using the TTL based.

    :returns: True if the token is expired, otherwise False
    """
    if "|" in token_line:
        expiry = token_line.strip().split("|")[1]
        if int(round(time.time())) > int(expiry):
            return True

    return False


def get_callback_token():
    """
    Generate a token and store it in the callback token file

    :returns: the token
    """
    snapdata_path = os.environ.get("SNAP_DATA")
    callback_token_file = "{}/credentials/callback-token.txt".format(snapdata_path)
    if os.path.exists(callback_token_file):
        with open(callback_token_file) as fp:
            token = fp.read()
    else:
        token = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(64))
        with open(callback_token_file, "w") as fp:
            fp.write("{}\n".format(token))
        try_set_file_permissions(callback_token_file)

    return token


def is_node_running_dqlite():
    """
    Check if we should use the dqlite joining process (join api version 2.0)

    :returns: True if dqlite is to be used, otherwise False
    """
    ha_lock = os.path.expandvars("${SNAP_DATA}/var/lock/ha-cluster")
    return os.path.isfile(ha_lock)


def is_node_dqlite_worker():
    """
    Check if this is a worker only node

    :returns: True if this is a worker node, otherwise False
    """
    ha_lock = os.path.expandvars("${SNAP_DATA}/var/lock/ha-cluster")
    clustered_lock = os.path.expandvars("${SNAP_DATA}/var/lock/clustered.lock")
    no_apiserver_proxy_lock = os.path.expandvars("${SNAP_DATA}/var/lock/no-apiserver-proxy")
    return (
        os.path.isfile(ha_lock)
        and os.path.isfile(clustered_lock)
        and not os.path.exists(no_apiserver_proxy_lock)
    )


def is_low_memory_guard_enabled():
    """
    Check if the low memory guard is enabled on this Node

    :returns: True if enabled, otherwise False
    """
    lock = os.path.expandvars("${SNAP_DATA}/var/lock/low-memory-guard.lock")
    return os.path.isfile(lock)


def get_dqlite_port():
    """
    What is the port dqlite listens on

    :return: the dqlite port
    """
    # We get the dqlite port from the already existing deployment
    snapdata_path = os.environ.get("SNAP_DATA")
    cluster_dir = "{}/var/kubernetes/backend".format(snapdata_path)
    dqlite_info = "{}/info.yaml".format(cluster_dir)
    port = 19001
    if os.path.exists(dqlite_info):
        with open(dqlite_info) as f:
            data = yaml.safe_load(f)
        if "Address" in data:
            port = data["Address"].split(":")[1]

    return port


def get_cluster_agent_port():
    """
    What is the cluster agent port

    :return: the port
    """
    cluster_agent_port = "25000"
    snapdata_path = os.environ.get("SNAP_DATA")
    filename = "{}/args/cluster-agent".format(snapdata_path)
    with open(filename) as fp:
        for _, line in enumerate(fp):
            if line.startswith("--bind"):
                port_parse = line.split(" ")
                port_parse = port_parse[-1].split("=")
                port_parse = port_parse[-1].split(":")
                if len(port_parse) > 1:
                    cluster_agent_port = port_parse[1].rstrip()
    return cluster_agent_port


def get_cluster_cidr():
    snapdata_path = os.environ.get("SNAP_DATA")
    filename = "{}/args/kube-proxy".format(snapdata_path)
    with open(filename) as fp:
        for _, line in enumerate(fp):
            if line.startswith("--cluster-cidr"):
                cidr_parse = line.split("=")
                if len(cidr_parse) > 1:
                    return cidr_parse[1].rstrip()
    return ""


def get_control_plane_nodes_internal_ips():
    """
    Return the internal IP of the nodes labeled running the control plane.

    :return: list of node internal IPs
    """
    snap_path = os.environ.get("SNAP")
    control_plane_label = "node.kubernetes.io/microk8s-controlplane=microk8s-controlplane"
    nodes_info = subprocess.check_output(
        "{}/microk8s-kubectl.wrapper get no -o json -l {}".format(
            snap_path, control_plane_label
        ).split()
    )
    info = json.loads(nodes_info.decode())
    node_ips = []
    for node_info in info["items"]:
        node_ip = get_internal_ip_from_get_node(node_info)
        node_ips.append(node_ip)
    return node_ips


def get_internal_ip_from_get_node(node_info):
    """
    Retrieves the InternalIp returned by kubectl get no -o json
    """
    for status_addresses in node_info["status"]["addresses"]:
        if status_addresses["type"] == "InternalIP":
            return status_addresses["address"]


def is_same_server(hostname, ip):
    """
    Check if the hostname is the same as the current node's hostname
    """
    try:
        hname, _, _ = socket.gethostbyaddr(ip)
        if hname == hostname:
            return True
    except socket.error:
        # Ignore any unresolvable IP by host, surely this is not from the same node.
        pass

    return False


def apply_cni_manifest(timeout_insec=60):
    """
    Apply the CNI yaml. If applying the manifest fails an exception is raised.
    :param timeout_insec: Try up to timeout seconds to apply the manifest.
    """
    yaml = "{}/args/cni-network/cni.yaml".format(os.environ.get("SNAP_DATA"))
    snap_path = os.environ.get("SNAP")
    cmd = "{}/microk8s-kubectl.wrapper apply -f {}".format(snap_path, yaml)
    deadline = datetime.datetime.now() + datetime.timedelta(seconds=timeout_insec)
    while True:
        try:
            check_output(cmd.split()).strip().decode("utf8")
            break
        except CalledProcessError as err:
            output = err.output.strip().decode("utf8").replace("\\n", "\n")
            print("Applying {} failed with {}".format(yaml, output))
            if datetime.datetime.now() > deadline:
                raise
            print("Retrying {}".format(cmd))
            time.sleep(3)


def cni_is_patched():
    """
    Detect if the cni.yaml manifest already has the hint for detecting nodes routing paths
    :return: True if calico knows where the rest of the nodes are.
    """
    yaml = "{}/args/cni-network/cni.yaml".format(os.environ.get("SNAP_DATA"))
    with open(yaml) as f:
        if "can-reach" in f.read():
            return True
        else:
            return False


def cni_yaml_exists():
    """
    Detect if the cni.yaml manifest exists.
    :return: True if calico cni.yaml exists.
    """
    yaml = "{}/args/cni-network/cni.yaml".format(os.environ.get("SNAP_DATA"))
    return os.path.exists(yaml)


def patch_cni(ip):
    """
    Patch the cni.yaml manifest with the proper hint on where the rest of the nodes are
    :param ip: The IP another k8s node has.
    """
    cni_yaml = "{}/args/cni-network/cni.yaml".format(os.environ.get("SNAP_DATA"))
    backup_file = "{}.backup".format(cni_yaml)
    with open(backup_file, "w") as back_fp:
        with open(cni_yaml, "r") as fp:
            for _, line in enumerate(fp):
                if "first-found" in line:
                    line = line.replace("first-found", "can-reach={}".format(ip))
                back_fp.write("{}".format(line))

    try_set_file_permissions(backup_file)
    shutil.copyfile(backup_file, cni_yaml)


def try_initialise_cni_autodetect_for_clustering(ip, apply_cni=True):
    """
    Try to initialise the calico route autodetection based on the IP
    provided, see https://docs.projectcalico.org/networking/ip-autodetection.
    If the cni manifest got changed by default it gets reapplied.
    :param ip: The IP another k8s node has.
    :param apply_cni: Should we apply the the manifest
    """
    if not cni_yaml_exists() or cni_is_patched():
        return True

    patch_cni(ip)
    if apply_cni:
        apply_cni_manifest()


def is_kubelite():
    """
    Do we run kubelite?
    """
    snap_data = os.environ.get("SNAP_DATA")
    if not snap_data:
        snap_data = "/var/snap/microk8s/current/"
    kubelite_lock = "{}/var/lock/lite.lock".format(snap_data)
    return os.path.exists(kubelite_lock)


def service(operation, service_name):
    """
    Restart a service. Handle case where kubelite is enabled.

    :param service_name: The service name
    :param operation: Operation to perform on the service
    """
    if service_name in ["apiserver", "proxy", "kubelet", "scheduler", "controller-manager"]:
        daemon = "microk8s.daemon-kubelite"
    else:
        daemon = "microk8s.daemon-{}".format(service_name)

    subprocess.check_call(["snapctl", operation, daemon])


def mark_no_cert_reissue():
    """
    Mark a node as being part of a cluster that should not re-issue certs
    on network changes
    """
    snap_data = os.environ.get("SNAP_DATA")
    lock_file = "{}/var/lock/no-cert-reissue".format(snap_data)
    open(lock_file, "a").close()
    os.chmod(lock_file, 0o700)


def unmark_no_cert_reissue():
    """
    Unmark a node as being part of a cluster. The node should now re-issue certs
    on network changes
    """
    snap_data = os.environ.get("SNAP_DATA")
    lock_file = "{}/var/lock/no-cert-reissue".format(snap_data)
    if os.path.exists(lock_file):
        os.unlink(lock_file)


def restart_all_services():
    """
    Restart all services
    """
    snap_path = os.environ.get("SNAP")
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


def get_token(name, tokens_file="known_tokens.csv"):
    """
    Get token from known_tokens file

    :param name: the name of the node
    :param tokens_file: the file where the tokens should go
    :returns: the token or None(if name doesn't exist)
    """
    snapdata_path = os.environ.get("SNAP_DATA")
    file = "{}/credentials/{}".format(snapdata_path, tokens_file)
    with open(file) as fp:
        for line in fp:
            if name in line:
                parts = line.split(",")
                return parts[0].rstrip()
    return None


def get_arg(key, file):
    """
    Get an argument from a file

    :param key: argument name
    :param file: the arguments file
    :return: value
    """
    snapdata_path = os.environ.get("SNAP_DATA")

    filename = "{}/args/{}".format(snapdata_path, file)
    with open(filename, "r+") as fp:
        for _, line in enumerate(fp):
            if line.startswith(key):
                parts = re.split(r" |=", line)
                return parts[-1]
    return None


def set_arg(key, value, file):
    """
    Set an argument to a file

    :param key: argument name
    :param value: value
    :param file: the arguments file
    """
    snapdata_path = os.environ.get("SNAP_DATA")

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


def is_token_auth_enabled():
    """
    Return True if token auth is enabled
    """
    if get_arg("--token-auth-file", "kube-apiserver"):
        return True
    else:
        return False


def enable_token_auth(token):
    """
    Turn on token auth and inject the admin token

    :param token: the admin token
    """
    snapdata_path = os.environ.get("SNAP_DATA")

    file = "{}/credentials/known_tokens.csv".format(snapdata_path)
    with open(file, "w") as fp:
        fp.write(f'{token},admin,admin,"system:masters"\n')

    try_set_file_permissions(file)
    set_arg("--token-auth-file", "${SNAP_DATA}/credentials/known_tokens.csv", "kube-apiserver")


def ca_one_line(ca):
    """
    The CA in one line
    :param ca: the ca
    :return: one line
    """
    return base64.b64encode(ca.encode("utf-8")).decode("utf-8")


def rebuild_x509_auth_client_configs():
    """
    Recreate all the client configs
    """
    if is_token_auth_enabled():
        set_arg("--token-auth-file", None, "kube-apiserver")

    subprocess.check_call(
        [f"{snap()}/actions/common/utils.sh", "create_user_certs_and_configs"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def get_valid_connection_parts(connection):
    """
    Ensure that connection has a valid format <master_ip>:<master_port>/<token>[/<fingerprint>]

    :param connection: the connection string
    :return: connection parts
    :raise:
        InvalidConnectionError: if connection string is not valid
    """
    connection_parts = connection.split("/")

    if len(connection_parts) not in [2, 3]:
        raise InvalidConnectionError(
            "Expected format: <master_IP>:<master_PORT>/<token>[/<fingerprint>]"
        )

    master_ep = connection_parts[0].split(":")
    if len(master_ep) != 2:
        raise InvalidConnectionError(
            "Expected format: <master_IP>:<master_PORT>/<token>[/<fingerprint>]"
        )

    try:
        ipaddress.ip_address(master_ep[0])
    except ValueError:
        raise InvalidConnectionError("Invalid master IP")

    try:
        port = int(master_ep[1])
        if port < 1 or port > 65535:
            raise InvalidConnectionError("Master PORT not in range 1:65535")
    except ValueError:
        raise InvalidConnectionError("Master PORT not a number")

    if len(connection_parts[1]) < TOKEN_ΜΙΝ_LEN:
        raise InvalidConnectionError(f"Cluster token size should be at least {TOKEN_ΜΙΝ_LEN} bytes")

    if len(connection_parts) == 3 and len(connection_parts[2]) < FINGERPRINT_MIN_LEN:
        raise InvalidConnectionError(f"Fingerprint should be at least {FINGERPRINT_MIN_LEN} bytes")

    return connection_parts
