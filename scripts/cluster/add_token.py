import os
import time
import argparse

cluster_tokens_file = os.path.expandvars("${SNAP_DATA}/credentials/cluster-tokens.txt")

def add_token_with_expiry(token, file, ttl=3600):
    """
    This method will add a token with expiry
    Expiry time is in seconds.

    Format of the item in the file: <token>|<expiry in seconds>

    :param str token: The token to add to the file
    :param str file: The file name for which the token will be written to
    :param ttl: How long the token should last before expiry, represented in seconds.
    """

    with open(file, 'a+') as fp:
        expiry = int(round(time.time())) + ttl 
        fp.write("{}|{}\n".format(token, expiry))


if __name__ == '__main__':

    # initiate the parser with a description
    parser = argparse.ArgumentParser(description='Microk8s add bootstrap token.', prog='microk8s add-token')
    parser.add_argument("--ttl", "-l", help="Specify how long the token is valid, before it expires", type=int,
                        default="86400")
    parser.add_argument( "--token", "-t", help="Specify the bootstrap token to add.", required=True)

    # read arguments from the command line
    args = parser.parse_args()

    ttl = args.ttl
    token = args.token

    add_token_with_expiry(token, cluster_tokens_file, ttl)

