#!/usr/bin/python3
import os
import argparse

import tempfile
import datetime
import subprocess
import tarfile
import os.path

from common.utils import (
    exit_if_no_permission,
    is_cluster_locked,
    is_ha_enabled,
    snap_data,
    safe_extract,
)


def get_kine_endpoint():
    """
    Return the default kine endpoint
    """
    return "unix://{}/var/kubernetes/backend/kine.sock:12379".format(snap_data())


def kine_exists():
    """
    Check the existence of the kine socket
    :return: True if the kine socket exists
    """
    kine_socket = get_kine_endpoint()
    kine_socket_path = kine_socket.replace("unix://", "")
    return os.path.exists(kine_socket_path)


def generate_backup_name():
    """
    Generate a filename based on the current time and date
    :return: a generated filename
    """
    now = datetime.datetime.now()
    return "backup-{}".format(now.strftime("%Y-%m-%d-%H-%M-%S"))


def run_command(command):
    """
    Run a command while printing the output
    :param command: the command to run
    :return: the return code of the command
    """
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    while True:
        output = process.stdout.readline()
        if (not output or output == "") and process.poll() is not None:
            break
        if output:
            print(output.decode().strip())
    rc = process.poll()
    return rc


def backup(fname=None, debug=False):
    """
    Backup the database to a provided file
    :param fname_tar: the tar file
    :param debug: show debug output
    """
    snap_path = os.environ.get("SNAP")
    kine_ep = get_kine_endpoint()

    if not fname:
        fname = generate_backup_name()
    if fname.endswith(".tar.gz"):
        fname = fname[:-7]
    fname_tar = "{}.tar.gz".format(fname)

    with tempfile.TemporaryDirectory() as tmpdirname:
        backup_cmd = (
            "{}/bin/k8s-dqlite migrator --endpoint {} --mode backup-dqlite --db-dir {}".format(
                snap_path, kine_ep, "{}/{}".format(tmpdirname, fname)
            )
        )
        if debug:
            backup_cmd = "{} {}".format(backup_cmd, "--debug")
        try:
            rc = run_command(backup_cmd)
            if rc > 0:
                print("Backup process failed. {}".format(rc))
                exit(1)
            with tarfile.open(fname_tar, "w:gz") as tar:
                tar.add(
                    "{}/{}".format(tmpdirname, fname),
                    arcname=os.path.basename("{}/{}".format(tmpdirname, fname)),
                )

            print("The backup is: {}".format(fname_tar))
        except subprocess.CalledProcessError as e:
            print("Backup process failed. {}".format(e))
            exit(2)


def restore(fname_tar, debug=False):
    """
    Restore the database from the provided file
    :param fname_tar: the tar file
    :param debug: show debug output
    """
    snap_path = os.environ.get("SNAP")
    kine_ep = get_kine_endpoint()
    with tempfile.TemporaryDirectory() as tmpdirname:
        with tarfile.open(fname_tar, "r:gz") as tar:
            safe_extract(tar, path=tmpdirname)
        if fname_tar.endswith(".tar.gz"):
            fname = fname_tar[:-7]
        else:
            fname = fname_tar
        fname = os.path.basename(fname)
        restore_cmd = (
            "{}/bin/k8s-dqlite migrator --endpoint {} --mode restore-to-dqlite --db-dir {}".format(
                snap_path, kine_ep, "{}/{}".format(tmpdirname, fname)
            )
        )
        if debug:
            restore_cmd = "{} {}".format(restore_cmd, "--debug")
        try:
            rc = run_command(restore_cmd)
            if rc > 0:
                print("Restore process failed. {}".format(rc))
                exit(3)
        except subprocess.CalledProcessError as e:
            print("Restore process failed. {}".format(e))
            exit(4)


if __name__ == "__main__":
    exit_if_no_permission()
    is_cluster_locked()

    if not kine_exists() or not is_ha_enabled():
        print("Please ensure the kubernetes apiserver is running and HA is enabled.")
        exit(10)

    # initiate the parser with a description
    parser = argparse.ArgumentParser(
        description="backup and restore the Kubernetes datastore.", prog="microk8s dbctl"
    )
    parser.add_argument("--debug", action="store_true", help="print debug output")
    commands = parser.add_subparsers(title="commands", help="backup and restore operations")
    restore_parser = commands.add_parser("restore")
    restore_parser.add_argument("backup-file", help="name of file with the backup")
    backup_parser = commands.add_parser("backup")
    backup_parser.add_argument("-o", metavar="backup-file", help="output filename")
    args = parser.parse_args()

    if "backup-file" in args:
        fname = vars(args)["backup-file"]
        print("Restoring from {}".format(fname))
        restore(fname, args.debug)
    elif "o" in args:
        print("Backing up the datastore")
        backup(vars(args)["o"], args.debug)
    else:
        parser.print_help()
