import json
import yaml
import os
import sys
import time
import argparse
import subprocess

from common.cluster.utils import is_node_running_dqlite, TOKEN_ΜΙΝ_LEN

try:
    from secrets import token_hex
except ImportError:
    from os import urandom

    def token_hex(nbytes=None):
        return urandom(nbytes).hex()


cluster_tokens_file = os.path.expandvars("${SNAP_DATA}/credentials/cluster-tokens.txt")
utils_sh_file = os.path.expandvars("${SNAP}/actions/common/utils.sh")
token_with_expiry = "{}|{}\n"
token_without_expiry = "{}\n"


def add_token_with_expiry(token, file, ttl):
    """
    This method will add a token to the token file with or without expiry
    Expiry time is in seconds.

    Format of the item in the file: <token>|<expiry in seconds>

    :param str token: The token to add to the file
    :param str file: The file name for which the token will be written to
    :param ttl: How long the token should last before expiry, represented in seconds.
    """

    with open(file, "a+") as fp:
        if ttl != -1:
            expiry = int(round(time.time())) + ttl
            fp.write(token_with_expiry.format(token, expiry))
        else:
            fp.write(token_without_expiry.format(token))


def run_util(*args, debug=False):
    env = os.environ.copy()
    prog = ["bash", utils_sh_file]
    prog.extend(args)

    if debug:
        print("\033[;1;32m+ %s\033[;0;0m" % " ".join(prog))

    result = subprocess.run(
        prog,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    try:
        result.check_returncode()
    except subprocess.CalledProcessError:
        print("Failed to call utility function.")
        sys.exit(1)

    return result.stdout.decode("utf-8").strip()


def get_network_info():
    """
    Obtain machine IP address(es) and cluster agent port.
    :return: tuple of default IP, all IPs, and cluster agent port
    """
    default_ip = run_util("get_default_ip")
    all_ips = run_util("get_ips").split(" ")
    port = run_util("cluster_agent_port")

    return (default_ip, all_ips, port)


def print_pretty(token, check):
    default_ip, all_ips, port = get_network_info()

    print("From the node you wish to join to this cluster, run the following:")
    print(f"microk8s join {default_ip}:{port}/{token}/{check}\n")

    if is_node_running_dqlite():
        print(
            "Use the '--worker' flag to join a node as a worker not running the control plane, eg:"
        )
        print(f"microk8s join {default_ip}:{port}/{token}/{check} --worker\n")

    print(
        "If the node you are adding is not reachable through the default interface you can use one of the following:"
    )
    for ip in all_ips:
        print(f"microk8s join {ip}:{port}/{token}/{check}")


def get_output_dict(token, check):
    _, all_ips, port = get_network_info()
    info = {
        "token": f"{token}/{check}",
        "urls": [f"{ip}:{port}/{token}/{check}" for ip in all_ips],
    }
    return info


def print_json(token, check):
    info = get_output_dict(token, check)
    print(json.dumps(info, indent=2))


def print_yaml(token, check):
    info = get_output_dict(token, check)
    print(yaml.dump(info, indent=2))


def print_short(token, check):
    default_ip, all_ips, port = get_network_info()
    print(f"microk8s join {default_ip}:{port}/{token}/{check}")
    for ip in all_ips:
        if ip != default_ip:
            print(f"microk8s join {ip}:{port}/{token}/{check}")


if __name__ == "__main__":

    # initiate the parser with a description
    parser = argparse.ArgumentParser(
        description="Produce a connection string for a node to join the cluster.",
        prog="microk8s add-node",
    )
    parser.add_argument(
        "--token-ttl",
        "-l",
        help="Specify how long the token is valid, before it expires. "
        'Value of "-1" indicates that the token is usable only once '
        "(i.e. after joining a node, the token becomes invalid)",
        type=int,
        default="-1",
    )
    parser.add_argument(
        "--token",
        "-t",
        help="Specify the bootstrap token to add, must be 32 characters long. "
        "Auto generates when empty.",
    )
    parser.add_argument(
        "--format",
        help="Format the output of the token in pretty, short, token, or token-check",
        default="pretty",
        choices={"pretty", "short", "token", "token-check", "json", "yaml"},
    )

    # read arguments from the command line
    args = parser.parse_args()

    ttl = args.token_ttl

    if args.token is not None:
        token = args.token
    else:
        token = token_hex(16)

    if len(token) < TOKEN_ΜΙΝ_LEN:
        print("Invalid token size.  It must be 32 characters long.")
        exit(1)

    add_token_with_expiry(token, cluster_tokens_file, ttl)
    check = run_util("server_cert_check")

    if args.format == "pretty":
        print_pretty(token, check)
    elif args.format == "short":
        print_short(token, check)
    elif args.format == "token-check":
        print(f"{token}/{check}")
    elif args.format == "json":
        print_json(token, check)
    elif args.format == "yaml":
        print_yaml(token, check)
    else:
        print(token)
