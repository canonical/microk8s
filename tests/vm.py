import string
import random
import time
import os
import signal
import subprocess
from os import path
from utils import (
    is_ipv6_configured,
)

profile = os.environ.get("LXC_PROFILE", "lxc/microk8s.profile")


class VM:
    """
    This class abstracts the backend we are using. It could be either multipass or lxc.
    """

    launch_config = """---
version: 0.1.0
extraCNIEnv:
  IPv4_SUPPORT: true
  IPv4_CLUSTER_CIDR: 10.3.0.0/16
  IPv4_SERVICE_CIDR: 10.153.183.0/24
  IPv6_SUPPORT: true
  IPv6_CLUSTER_CIDR: fd02::/64
  IPv6_SERVICE_CIDR: fd99::/108
extraSANs:
  - 10.153.183.1"""

    def __init__(self, backend=None, attach_vm=None, enable_ipv6=True):
        """Detect the available backends and instantiate a VM.

        If `attach_vm` is provided we just make sure the right MicroK8s is deployed.
        :param backend: either multipass of lxc
        :param attach_vm: the name of the VM we want to reuse
        :param enable_ipv6: if set, IPv6 support is enabled in the launch config (enabled by default)
        """
        rnd_letters = "".join(random.choice(string.ascii_lowercase) for i in range(6))
        self.backend = backend
        self.vm_name = "vm-{}".format(rnd_letters)
        self.attached = False
        if attach_vm:
            self.attached = True
            self.vm_name = attach_vm

        if not enable_ipv6:
            self.launch_config = self.launch_config.replace(
                "IPv6_SUPPORT: true", "IPv6_SUPPORT: false"
            )

    def setup(self, channel_or_snap):
        """
        Setup the VM with the right snap.

        :param channel_or_snap: the snap channel or the path to the local snap build
        """
        if (path.exists("/snap/bin/multipass") and not self.backend) or self.backend == "multipass":
            print("Creating mulitpass VM")
            self.backend = "multipass"
            self._setup_multipass(channel_or_snap)

        elif (path.exists("/snap/bin/lxc") and not self.backend) or self.backend == "lxc":
            print("Creating lxc VM")
            self.backend = "lxc"
            self._setup_lxc(channel_or_snap)
        else:
            raise Exception("Need to install multipass or lxc")

    def _setup_lxc(self, channel_or_snap):
        if not self.attached:
            profiles = subprocess.check_output("/snap/bin/lxc profile list".split())
            if "microk8s" not in profiles.decode():
                subprocess.check_call("/snap/bin/lxc profile copy default microk8s".split())
                with open(profile, "r+") as fp:
                    profile_string = fp.read()
                    process = subprocess.Popen(
                        "/snap/bin/lxc profile edit microk8s".split(),
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                    )
                    process.stdin.write(profile_string.encode())
                    process.stdin.close()

            subprocess.check_call(
                "/snap/bin/lxc launch -p default -p microk8s ubuntu:18.04 {}".format(
                    self.vm_name
                ).split()
            )
            time.sleep(20)
            if is_ipv6_configured():
                self._load_launch_configuration_lxc()

            if channel_or_snap.startswith("/"):
                self._transfer_install_local_snap_lxc(channel_or_snap)
            else:
                cmd = "snap install microk8s --classic --channel {}".format(channel_or_snap)
                time.sleep(20)
                print("About to run {}".format(cmd))
                output = ""
                attempt = 0
                while attempt < 3:
                    try:
                        output = self.run(cmd)
                        break
                    except ChildProcessError:
                        time.sleep(10)
                        attempt += 1
                print(output.decode())
        else:
            if is_ipv6_configured():
                self._load_launch_configuration_lxc()

            if channel_or_snap.startswith("/"):
                self._transfer_install_local_snap_lxc(channel_or_snap)
            else:
                cmd = "/snap/bin/lxc exec {}  -- ".format(self.vm_name).split()
                cmd.append("sudo snap refresh microk8s --channel {}".format(channel_or_snap))
                subprocess.check_call(cmd)

    def _load_launch_configuration_lxc(self):
        # Set launch configurations before installing microk8s
        print("Setting launch configurations")
        self.run("mkdir -p /var/snap/microk8s/common/")
        file_path = "microk8s.yaml"
        print(self.launch_config)
        with open(file_path, "w") as file:
            file.write(self.launch_config)

        # Copy the file to the VM
        cmd = "lxc file push {} {}/var/snap/microk8s/common/.microk8s.yaml".format(
            file_path, self.vm_name
        ).split()
        subprocess.check_output(cmd)
        os.remove(file_path)

    def _transfer_install_local_snap_lxc(self, channel_or_snap):
        try:
            print("Installing snap from {}".format(channel_or_snap))
            cmd_prefix = "/snap/bin/lxc exec {}  -- script -e -c".format(self.vm_name).split()
            cmd = ["rm -rf /var/tmp/microk8s.snap"]
            subprocess.check_output(cmd_prefix + cmd)
            cmd = "lxc file push {} {}/var/tmp/microk8s.snap".format(
                channel_or_snap, self.vm_name
            ).split()
            subprocess.check_output(cmd)
            cmd = ["snap install /var/tmp/microk8s.snap --dangerous --classic"]
            subprocess.check_output(cmd_prefix + cmd)
            time.sleep(20)
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            raise

    def _setup_multipass(self, channel_or_snap):
        if not self.attached:
            subprocess.check_call(
                "/snap/bin/multipass launch 18.04 -n {} -m 2G".format(self.vm_name).split()
            )
            if is_ipv6_configured():
                self._load_launch_configuration_multipass()

            if channel_or_snap.startswith("/"):
                self._transfer_install_local_snap_multipass(channel_or_snap)
            else:
                subprocess.check_call(
                    "/snap/bin/multipass exec {}  -- sudo "
                    "snap install microk8s --classic --channel {}".format(
                        self.vm_name, channel_or_snap
                    ).split()
                )
        else:
            if is_ipv6_configured():
                self._load_launch_configuration_multipass()
            if channel_or_snap.startswith("/"):
                self._transfer_install_local_snap_multipass(channel_or_snap)
            else:
                subprocess.check_call(
                    "/snap/bin/multipass exec {}  -- sudo "
                    "snap refresh microk8s --channel {}".format(
                        self.vm_name, channel_or_snap
                    ).split()
                )

    def _load_launch_configuration_multipass(self):
        # Set launch configurations before installing microk8s
        print("Setting launch configurations")
        self.run("mkdir -p /var/snap/microk8s/common/")
        self.run("chmod 777 /var/snap/microk8s/common/")
        file_path = "microk8s.yaml"
        print(self.launch_config)
        with open(file_path, "w") as file:
            file.write(self.launch_config)

        # Copy the file to the VM
        subprocess.check_call(
            "/snap/bin/multipass transfer {} {}:/var/snap/microk8s/common/.microk8s.yaml".format(
                file_path, self.vm_name
            ).split()
        )
        os.remove(file_path)

    def _transfer_install_local_snap_multipass(self, channel_or_snap):
        print("Installing snap from {}".format(channel_or_snap))
        subprocess.check_call(
            "/snap/bin/multipass transfer {} {}:/var/tmp/microk8s.snap".format(
                channel_or_snap, self.vm_name
            ).split()
        )
        subprocess.check_call(
            "/snap/bin/multipass exec {}  -- sudo "
            "snap install /var/tmp/microk8s.snap --classic --dangerous".format(self.vm_name).split()
        )

    def run(self, cmd):
        """
        Run a command
        :param cmd: the command we are running.
        :return: the output of the command
        """
        if self.backend == "multipass":
            output = subprocess.check_output(
                "/snap/bin/multipass exec {} -- sudo " "{}".format(self.vm_name, cmd).split()
            )
            return output
        elif self.backend == "lxc":
            cmd_prefix = "/snap/bin/lxc exec {}  -- ".format(self.vm_name)
            with subprocess.Popen(
                cmd_prefix + cmd, shell=True, stdout=subprocess.PIPE, preexec_fn=os.setsid
            ) as process:
                try:
                    output = process.communicate(timeout=300)[0]
                    if process.returncode != 0:
                        raise ChildProcessError("Failed to run command")
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)  # send signal to the process group
                    print("Process timed out")
                    output = process.communicate()[0]
            return output
        else:
            raise Exception("Not implemented for backend {}".format(self.backend))

    def run_in_background(self, cmd, with_sudo=True):
        """
        Run a command
        :param cmd: the command we are running.
        :param with_sudo: whether to run the cmd with sudo (only multipass).
        :return: the output of the command
        """
        if self.backend == "multipass":
            os.spawnlp(
                os.P_NOWAIT,
                "/snap/bin/multipass exec {}  -- {} "
                "{}".format(self.vm_name, "sudo" if with_sudo else "", cmd).split(),
            )
        else:
            raise Exception("Not implemented for backend {}".format(self.backend))

    def transfer_file(self, file_path, remote_path):
        """
        Transfer a file to the VM.
        """
        print("Transferring {} to {}".format(file_path, remote_path))
        if self.backend == "multipass":
            subprocess.check_call(
                "/snap/bin/multipass transfer {} {}:{} ".format(
                    file_path, self.vm_name, remote_path
                ).split()
            )
        elif self.backend == "lxc":
            subprocess.check_call(
                "/snap/bin/lxc file push {} {}{}".format(
                    file_path, self.vm_name, remote_path
                ).split()
            )

    def release(self):
        """
        Release a VM.
        """
        print("Destroying VM in {}".format(self.backend))
        if self.backend == "multipass":
            subprocess.check_call("/snap/bin/multipass stop {}".format(self.vm_name).split())
            subprocess.check_call("/snap/bin/multipass delete {}".format(self.vm_name).split())
        elif self.backend == "lxc":
            subprocess.check_call("/snap/bin/lxc stop {}".format(self.vm_name).split())
            subprocess.check_call("/snap/bin/lxc delete {}".format(self.vm_name).split())
