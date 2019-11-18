import os
import shutil


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

