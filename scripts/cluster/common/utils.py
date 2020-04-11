import os
import shutil
import time


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
    
    :param token: the token to be removed
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
                if "|" not in line :
                    if line.strip() == token:
                        continue
                back_fp.write("{}".format(line))

    shutil.copyfile(backup_file, file)


def is_token_expired(token_line):
    """
    Checks if the token in the file is expired, when using the TTL based.
    """
    if "|" in token_line:
        expiry = token_line.strip().split('|')[1]
        if int(round(time.time())) > int(expiry):
            return True

    return False    