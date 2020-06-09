import os
import time
import argparse

try:
    from secrets import token_hex
except ImportError:
    from os import urandom

    def token_hex(nbytes=None):
        return urandom(nbytes).hex()


cluster_tokens_file = os.path.expandvars("${SNAP_DATA}/credentials/cluster-tokens.txt")
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

    with open(file, 'a+') as fp:
        if ttl != -1:
            expiry = int(round(time.time())) + ttl
            fp.write(token_with_expiry.format(token, expiry))
        else:
            fp.write(token_without_expiry.format(token))


if __name__ == '__main__':

    # initiate the parser with a description
    parser = argparse.ArgumentParser(
        description='Produce a connection string for a node to join the cluster.',
        prog='microk8s add-node',
    )
    parser.add_argument(
        "--token-ttl",
        "-l",
        help="Specify how long the token is valid, before it expires. "
        "Value of \"-1\" indicates that the token is usable only once "
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

    # read arguments from the command line
    args = parser.parse_args()

    ttl = args.token_ttl

    if args.token is not None:
        token = args.token
    else:
        token = token_hex(16)

    if len(token) < 32:
        print("Invalid token size.  It must be 32 characters long.")
        exit(1)

    add_token_with_expiry(token, cluster_tokens_file, ttl)
