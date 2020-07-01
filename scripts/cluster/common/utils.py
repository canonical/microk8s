import os
import shutil
import time
import string
import random
import yaml


def try_set_file_permissions(file):
    """
    Try setting the ownership group and permission of the file

    :param file: full path and filename
    """

    os.chmod(file, 0o660)
    try:
        shutil.chown(file, group='microk8s')
    except:
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
    with open(backup_file, 'w') as back_fp:
        with open(file, 'r') as fp:
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
    with open(backup_file, 'w') as back_fp:
        with open(file, 'r') as fp:
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
        expiry = token_line.strip().split('|')[1]
        if int(round(time.time())) > int(expiry):
            return True

    return False


def get_callback_token():
    """
    Generate a token and store it in the callback token file

    :returns: the token
    """
    snapdata_path = os.environ.get('SNAP_DATA')
    callback_token_file = "{}/credentials/callback-token.txt".format(snapdata_path)
    if os.path.exists(callback_token_file):
        with open(callback_token_file) as fp:
            token = fp.read()
    else:
        token = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(64))
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
    snapdata_path = os.environ.get('SNAP_DATA')
    cluster_dir = "{}/var/kubernetes/backend".format(snapdata_path)
    dqlite_info = "{}/info.yaml".format(cluster_dir)
    port = 19001
    if os.path.exists(dqlite_info):
        with open(dqlite_info) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        if 'Address' in data:
            port = data['Address'].split(':')[1]

    return port


def get_cluster_agent_port():
    """
    What is the cluster agent port

    :return: the port
    """
    cluster_agent_port = "25000"
    snapdata_path = os.environ.get('SNAP_DATA')
    filename = "{}/args/cluster-agent".format(snapdata_path)
    with open(filename) as fp:
        for _, line in enumerate(fp):
            if line.startswith("--bind"):
                port_parse = line.split(' ')
                port_parse = port_parse[-1].split('=')
                port_parse = port_parse[-1].split(':')
                if len(port_parse) > 1:
                    cluster_agent_port = port_parse[1].rstrip()
    return cluster_agent_port


def get_arg(key, file):
    """
    Get an argument from an arguments file

    :param key: the argument we look for
    :param file: the arguments file to search in
    :returns: the value of the argument or None(if the key doesn't exist)
    """
    snapdata_path = os.environ.get('SNAP_DATA')
    filename = "{}/args/{}".format(snapdata_path, file)
    with open(filename) as fp:
        for _, line in enumerate(fp):
            if line.startswith(key):
                args = line.split(' ')
                args = args[-1].split('=')
                return args[-1].rstrip()
    return None
