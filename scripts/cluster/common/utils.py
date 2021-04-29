import os
import shutil
import subprocess
import time
import string
import random
import datetime
from subprocess import check_output, CalledProcessError

import yaml
import socket


def try_set_file_permissions(file):
    """
    Try setting the ownership group and permission of the file

    :param file: full path and filename
    """

    os.chmod(file, 0o660)
    try:
        shutil.chown(file, group="microk8s")
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
            data = yaml.load(f, Loader=yaml.FullLoader)
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
    if cni_is_patched():
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
    if (
        service_name == "apiserver"
        or service_name == "proxy"
        or service_name == "kubelet"
        or service_name == "scheduler"
        or service_name == "controller-manager"
    ) and is_kubelite():
        subprocess.check_call("snapctl {} microk8s.daemon-kubelite".format(operation).split())
    else:
        subprocess.check_call(
            "snapctl {} microk8s.daemon-{}".format(operation, service_name).split()
        )


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
