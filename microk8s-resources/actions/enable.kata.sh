#!/usr/bin/env python3

import click
import os
import subprocess
import sys
from tempfile import mkstemp
from shutil import move, copymode
from os import fdopen, remove


def mark_kata_enabled():
    """
    Mark the kata addon as enabled by creating the kata.enabled
    """
    try:
        snapdata_path = os.environ.get("SNAP_DATA")
        lock_fname = "{}/var/lock/kata.enabled".format(snapdata_path)
        subprocess.call(["sudo", "touch", lock_fname])
    except (subprocess.CalledProcessError):
        print("Failed to mark the kata addon as enabled.")
        sys.exit(4)


def apply_runtime_manifest():
    """
    Apply the manifest containing the definition of the kata runtimeClassName
    """
    try:
        snap_path = os.environ.get("SNAP")
        manifest = "{}/actions/kata/runtime.yaml".format(snap_path)
        subprocess.call(["{}/microk8s-kubectl.wrapper".format(snap_path), "apply", "-f", manifest])
    except (subprocess.CalledProcessError):
        print("Failed to apply the runtime manifest.")
        sys.exit(5)


def restart_containerd():
    """
    Restart the containerd service
    """
    try:
        print("Restarting containerd")
        subprocess.call(["sudo", "systemctl", "restart", "snap.microk8s.daemon-containerd"])
    except (subprocess.CalledProcessError):
        print(
            "Failed to restart containerd. Please, yry to 'microk8s stop' and 'microk8s start' manually."
        )
        sys.exit(3)


def configure_containerd(kata_path):
    """
    Configure the containerd PATH so it finds the kata runtime binary
    """
    snapdata_path = os.environ.get("SNAP_DATA")
    containerd_env_file = "{}/args/containerd-env".format(snapdata_path)
    # Create temp file
    fh, abs_path = mkstemp()
    with fdopen(fh, "w") as tmp_file:
        with open(containerd_env_file) as conf_file:
            for line in conf_file:
                if "KATA_PATH=" in line:
                    line = 'KATA_PATH="{}"\n'.format(kata_path)
                tmp_file.write(line)

    copymode(containerd_env_file, abs_path)
    remove(containerd_env_file)
    move(abs_path, containerd_env_file)


def is_kvm_supported():
    """
    Check if the CPU supports virtualisation needed for Kata.
    """
    with open("/proc/cpuinfo") as f:
        for line in f.readlines():
            if "vmx" in line or "svm" in line:
                return True
    return False


def print_next_steps():
    print()
    print()
    print("To use the kata runtime set the 'kata' runtimeClassName, eg:")
    print()
    print("kind: Pod")
    print("metadata:")
    print("  name: nginx-kata")
    print("spec:")
    print("  runtimeClassName: kata")
    print("  containers:")
    print("  - name: nginx")
    print("    image: nginx")
    print()


@click.command()
@click.option(
    "--runtime-path",
    default=None,
    help="The path to the kata container runtime binaries.",
)
def kata(runtime_path):
    """
    Enable the kata runtime. Either snap install the kata binaries or use a path to already deployed
    kata binaries. Note the kata binary must be called kata-runtime
    """
    if not is_kvm_supported():
        print("Virtualisation is not supported on this CPU, exiting.")
        sys.exit(6)

    if not runtime_path:
        try:
            print("Installing kata-containers snap")
            subprocess.call(["sudo", "snap", "install", "kata-containers", "--classic"])
            kata_path = "/snap/kata-containers/current/usr/bin/"
        except (subprocess.CalledProcessError):
            print("Failed to install kata-containers snap.")
            print(
                "Use the --runtime-path argument to point to the kata containers runtime binaries."
            )
            sys.exit(1)
    else:
        kata_path = runtime_path

    if not os.path.exists("{}/kata-runtime".format(kata_path)):
        print("Kata runtime binaries was not found under {}.".format(kata_path))
        print("Use the --runtime-path argument to point to the right location.")
        sys.exit(2)

    configure_containerd(kata_path)
    restart_containerd()
    apply_runtime_manifest()
    mark_kata_enabled()
    print_next_steps()


if __name__ == "__main__":
    kata(prog_name="microk8s enable kata")
