#!/bin/env python3

import datetime
import json
import time
from subprocess import CalledProcessError

import yaml

from testnode.addons import (
    Dashboard,
    Dns,
    Fluentd,
    Gpu,
    Ingress,
    Jaeger,
    Metallb,
    MetricsServer,
    Registry,
    Storage,
)


class Executor:
    """Node aware command executor"""

    prefix = []

    def __init__(self, node):
        """Initialize an executor"""
        self.node = node

    def run(self, cmd):
        full_cmd = self.prefix + cmd

        return self.node.check_output(full_cmd)

    def _get_deadline(self, timeout):
        deadline = datetime.datetime.now() + datetime.timedelta(
            seconds=timeout * self.node._timeout_coefficient
        )
        return deadline

    def run_until_success(self, cmd, timeout=60):
        """
        Run a command until it succeeds or times out.
        Args:
            cmd: Command to run
            timeout: Time out in seconds

        Returns: The string output of the command

        """
        deadline = self._get_deadline(timeout)

        while True:
            try:
                output = self.run(cmd)

                return output
            except CalledProcessError:
                if datetime.datetime.now() > deadline:
                    raise
                print("Retrying {}".format(cmd))
                time.sleep(1)


class Snap(Executor):
    """Node aware SNAP executor"""

    prefix = ["snap"]

    def install(self, snap, channel=None, classic=False, dangerous=False):
        """Install a snap"""
        cmd = ["install", f"{snap}"]

        if channel:
            cmd.append(f"--channel={channel}")
        if classic:
            cmd.append("--classic")
        if dangerous:
            cmd.append("--dangerous")
        self.run_until_success(cmd)

    def refresh(self, snap, channel, classic=False):
        """Refresh a snap"""
        cmd = ["refresh", f"{snap}", f"--channel={channel}"]

        if classic:
            cmd.append("--classic")
        self.run_until_success(cmd)

    def restart(self, snap):
        """ Restart a snap """
        cmd = ["restart", f"{snap}"]

        self.run_until_success(cmd)


class Docker(Executor):
    """Node aware Docker executor"""

    prefix = ["docker"]

    def set_config(self, config, merge=True):
        if merge:
            config_path = "/var/snap/docker/current/config/daemon.json"
            config_string = self.node.check_output(["cat", f"{config_path}"])
            config_loaded = json.loads(config_string)
            config_loaded.update(config)
        else:
            config_loaded = config

        config_new_string = json.dumps(config_loaded)
        self.node.write(config_path, config_new_string)
        self.node.snap.restart("docker")

    def set_storage_driver(self, driver="vfs"):
        self.set_config({"storage-driver": driver}, True)

    def cmd(self, args):
        self.run_until_success(args)


class Kubectl(Executor):
    """Node aware Microk8s Kubectl executor"""

    prefix = ["kubectl"]

    def __init__(self, *args, prefix=None, **kwargs):
        super().__init__(*args, **kwargs)

        if prefix and isinstance(prefix, list):
            self.prefix = prefix + self.prefix

    def result(self, cmds, yml):
        """Return commands optionally as yaml"""

        if yml:
            cmds.append("-oyaml")

            return yaml.safe_load(self.run_until_success(cmds))

        return self.run_until_success(cmds)

    def get(self, args, yml=True):

        cmd = ["get"]
        cmd.extend(args)

        return self.result(cmd, yml)

    def apply(self, args, yml=True):

        cmd = ["apply"]
        cmd.extend(args)

        return self.result(cmd, yml)

    def delete(self, args, yml=True):
        cmd = ["delete"]
        cmd.extend(args)

        return self.result(cmd, yml)


class Microk8s(Executor):
    """Node aware MicroK8s executor"""

    prefix = [
        "/snap/bin/microk8s",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kubectl = Kubectl(self.node, prefix=self.prefix)
        self.dns = Dns(self.node)
        self.dashboard = Dashboard(self.node)
        self.storage = Storage(self.node)
        self.ingress = Ingress(self.node)
        self.gpu = Gpu(self.node)
        self.registry = Registry(self.node)
        self.metrics_server = MetricsServer(self.node)
        self.fluentd = Fluentd(self.node)
        self.jaeger = Jaeger(self.node)
        self.metallb = Metallb(self.node)

    @property
    def config(self):
        """Microk8s config"""
        cmd = ["config"]

        return self.run_until_success(cmd)

    def get_config(self):
        """Return this nodes config"""

        return self.config

    def start(self):
        """Start microks"""
        cmd = ["start"]

        return self.run_until_success(cmd)

    def status(self):
        """Microk8s status"""
        cmd = ["status"]

        return self.run_until_success(cmd)

    def enable(self, addons):
        """Enable a addons"""
        cmd = ["enable"]
        cmd.extend(addons)

        result = self.run_until_success(cmd)

        return result

    def wait_until_running(self, timeout=60):
        """Wait until the status returns running"""
        deadline = self._get_deadline(timeout)

        while True:
            status = self.status()

            if "microk8s is running" in status:
                return
            elif datetime.datetime.now() > deadline:
                raise TimeoutError("Timeout waiting for microk8s status")
            time.sleep(1)

    def wait_until_service_running(self, service, timeout=60):
        """Wait until a microk8s service is running"""
        deadline = self._get_deadline(timeout)

        cmd = [
            "systemctl",
            "is-active",
            f"snap.microk8s.daemon-{service}.service",
        ]

        while True:
            service_status = self.node.cmd.run_until_success(cmd)

            if "active" in service_status:
                return
            elif datetime.datetime.now() > deadline:
                raise TimeoutError(f"Timeout waiting for {service} to become active")
            time.sleep(1)
