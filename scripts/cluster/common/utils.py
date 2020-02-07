import os
import shutil
import string
from random import random


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


def get_callback_token():
    """
    Generate a token and store it in the callback token file

    :return: the token
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
