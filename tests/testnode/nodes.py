#!/bin/env python3

from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess

import yaml

import pylxd
from testnode.api import Kubernetes
from testnode.executors import Docker, Executor, Kubectl, Microk8s, Snap


class Node:
    """A test node with executors"""

    def __init__(self):
        self.cmd = Executor(self)
        self.snap = Snap(self)
        self.kubectl = Kubectl(self)
        self.docker = Docker(self)
        self.microk8s = Microk8s(self)
        self.kubernetes = Kubernetes(config=self.microk8s.get_config)
        self._timeout_coefficient = 1.0

    def set_timeout_coefficient(self, coefficient):
        self._timeout_coefficient = float(coefficient)


class Lxd(Node):
    """LXD Node type for testing in containers"""

    profile_name = "microk8s"

    def __init__(self, image=None, name=None):
        super().__init__()
        print("Creating a LXD node")
        self.client = pylxd.Client()

        if name:
            print(f"getting container {name}")
            self.container = self.client.containers.get(name)
        elif image:
            self.__setup_profile()
            print(f"creating container {image}")
            config = {
                "name": f"{self.__class__.__name__.lower()}-{self.__hash__()}",
                "source": {
                    "type": "image",
                    "mode": "pull",
                    "server": "https://cloud-images.ubuntu.com/daily",
                    "protocol": "simplestreams",
                    "alias": image,
                },
                "profiles": ["default", self.profile_name],
            }
            self.container = self.client.containers.create(config=config, wait=True)

    def __setup_profile(self):
        """Setup microk8s profile if not present"""

        if self.client.profiles.exists(self.profile_name):
            return

        cwd = Path(__file__).parent
        pfile = cwd / "lxc" / "microk8s.profile"
        with pfile.open() as f:
            profile = yaml.safe_load(f)
        self.client.profiles.create(self.profile_name, profile["config"], profile["devices"])

    def start(self):
        """Start the node"""

        return self.container.start(wait=True)

    def stop(self):
        """Stop the node"""

        return self.container.stop(wait=True)

    def delete(self):
        """Delete the node"""

        return self.container.delete()

    def check_output(self, cmd):
        """Check execution of a command"""
        exit_code, stdout, stderr = self.container.execute(cmd)
        try:
            CompletedProcess(cmd, exit_code, stdout, stderr).check_returncode()
        except CalledProcessError as e:
            print(f"Stdout: {stdout}\r" f"Stderr: {stderr}\r")
            raise e

        return stdout

    def write(self, dest, contents):
        """Write contents at destination on node"""

        return self.container.files.put(dest, contents)

    def put(self, dest, source):
        """Copy a file to the destination on node"""

        src = Path(source)
        with src.open(mode="rb") as f:
            return self.write(dest, f.read())

    def get_primary_address(self):
        """Get the primary interface ip address"""

        return self.container.state().network["eth0"]["addresses"][0]["address"]


class XenialLxd(Lxd):
    """Xenial LXD Node"""

    def __init__(self, name=None):
        if name:
            super().__init__(name=name)
        else:
            super().__init__(image="xenial/amd64")


class BionicLxd(Lxd):
    """Bionic LXD Node"""

    def __init__(self, name=None):
        if name:
            super().__init__(name=name)
        else:
            super().__init__(image="bionic/amd64")


class FocalLxd(Lxd):
    """Focal LXD Node"""

    def __init__(self, name=None):
        if name:
            super().__init__(name=name)
        else:
            super().__init__(image="focal/amd64")
