#!/usr/bin/env python3

import click
import os
import subprocess
import sys
from tempfile import mkstemp
from shutil import move, copymode
from os import fdopen, remove


def mark_kata_disabled():
    """
    Mark the kata addon as enabled by removing the kata.enabled lock
    """
    try:
        snapdata_path = os.environ.get("SNAP_DATA")
        lock_fname = "{}/var/lock/kata.enabled".format(snapdata_path)
        subprocess.call(['sudo', 'rm', lock_fname])
    except (subprocess.CalledProcessError):
        print("Failed to mark the kata addon as disabled." )
        sys.exit(4)

def delete_runtime_manifest():
    try:
        snap_path = os.environ.get("SNAP")
        manifest = "{}/actions/kata/runtime.yaml".format(snap_path)
        subprocess.call(["{}/microk8s-kubectl.wrapper".format(snap_path), "delete", "-f", manifest])
    except (subprocess.CalledProcessError):
        print("Failed to apply the runtime manifest." )
        sys.exit(5)


def restart_containerd():
    try:
        print("Restarting containerd")
        subprocess.call(['sudo', 'systemctl', 'restart', 'snap.microk8s.daemon-containerd'])
    except (subprocess.CalledProcessError):
        print("Failed to restart containerd. Please, yry to 'microk8s stop' and 'microk8s start' manualy." )
        sys.exit(3)


def configure_containerd():
    """
    Configure the containerd PATH by removing the kata runtime binary
    """
    snapdata_path = os.environ.get("SNAP_DATA")
    containerd_env_file = "{}/args/containerd-env".format(snapdata_path)
    #Create temp file
    fh, abs_path = mkstemp()
    with fdopen(fh,'w') as tmp_file:
        with open(containerd_env_file) as conf_file:
            for line in conf_file:
                if "KATA_PATH=" in line:
                  line = "KATA_PATH=\n"
                tmp_file.write(line)

    copymode(containerd_env_file, abs_path)
    remove(containerd_env_file)
    move(abs_path, containerd_env_file)


@click.command()
def kata():
    """
    Disable the kata runtime. Mark it as disabled, delete the runtimeClassName but do not remove the
    kata runtime because we do not know if it is used by any other application.
    """
    print("Configuring containerd")
    configure_containerd()
    restart_containerd()
    print("Deleting kata runtime manifest")
    delete_runtime_manifest()
    mark_kata_disabled()


if __name__ == "__main__":
    kata(prog_name="microk8s disable kata")
