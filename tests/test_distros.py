#!/bin/env python3

import os
from distutils.util import strtobool
from pathlib import Path

import yaml

from testnode.nodes import BionicLxd, FocalLxd, Node, XenialLxd


def pytest_generate_tests(metafunc):
    """Allow per class parameter definitions"""
    # called once per each test function
    try:
        funcarglist = metafunc.cls.params[metafunc.function.__name__]
    except KeyError:
        # No parameters for this test
        return
    argnames = sorted(funcarglist[0])
    metafunc.parametrize(
        argnames, [[funcargs[name] for name in argnames] for funcargs in funcarglist]
    )


class InstallTests:
    """MicroK8s Install Tests"""

    node_type = None
    keep_node = bool(strtobool(os.environ.get("MK8S_KEEP_NODE", "false")))
    existing_node = os.environ.get("MK8S_EXISTING_NODE", None)
    install_version = os.environ.get("MK8S_INSTALL_VERSION", "beta")
    timeout_coefficient = os.environ.get("MK8S_TIMEOUT_COEFFICIENT", 1.0)

    addons = [
        {"addon": "dns", "input": ""},
        {"addon": "dashboard", "input": ""},
        {"addon": "storage", "input": ""},
        {"addon": "ingress", "input": ""},
        {"addon": "registry", "input": ""},
        {"addon": "metrics_server", "input": ""},
        {"addon": "fluentd", "input": ""},
        {"addon": "jaeger", "input": ""},
        {
            "addon": "metallb",
            "input": "192.168.0.105-192.168.0.105,192.168.0.110-192.168.0.111,192.168.1.240/28",
        },
    ]

    params = {"test_addon": addons}

    def setup_class(self):
        """Setup the tests"""
        print("Setting up Install tests")

        if self.existing_node:
            print(f"Using existing node: {self.existing_node}")
            self.node = self.node_type(name=self.existing_node)
        else:
            print("Creating new node")
            self.node = self.node_type()
            self.node.start()

        self.node.timeout_coefficient = self.timeout_coefficient
        self.node.kubernetes.set_timeout_coefficient(self.timeout_coefficient)

    def teardown_class(self):
        if self.keep_node:
            return
        self.node.stop()
        self.node.delete()

    def test_collection(self):
        """Test that this test is collected"""

        return True

    def test_node_setup(self):
        """Test that expceted nodes exist"""
        assert isinstance(self.node, Node)

    def test_snap_install(self):
        """Test installing a snap"""
        self.node.snap.install("microk8s", channel=self.install_version, classic=True)
        # Required for registry
        self.node.snap.install("docker", channel="stable", classic=True)
        self.node.docker.set_storage_driver("vfs")

    def test_start_microk8s(self):
        """Test starting microk8s"""
        self.node.microk8s.start()
        self.node.microk8s.wait_until_running()
        status = self.node.microk8s.status()
        assert "microk8s is running" in status

    def test_get_kubeconfig(self):
        """Test retrieving the kubeconfig"""
        config = yaml.safe_load(self.node.microk8s.config)
        assert config["clusters"][0]["name"] == "microk8s-cluster"

    def test_nodes_ready(self):
        """Test nodes are ready"""
        ready = self.node.kubernetes.wait_nodes_ready(1)
        assert ready == 1

    def test_addon(self, addon, input):
        """Test enabling addon"""
        addon_attr = getattr(self.node.microk8s, addon)
        if input:
            result = addon_attr.enable(input)
        else:
            result = addon_attr.enable()
        assert "Nothing to do for" not in result

        if input:
            addon_attr.validate(input)
        else:
            addon_attr.validate()


class UpgradeTests(InstallTests):
    """Upgrade after an install"""

    upgrade_version = os.environ.get("MK8S_UPGRADE_VERSION", "edge")

    params = dict(**InstallTests.params, **{"test_retest_addon": InstallTests.addons})

    def setup_class(self):
        """Setup the tests"""
        super().setup_class(self)
        print("Setting up Upgrade tests")
        if self.upgrade_version.endswith(".snap"):
            src = Path(self.upgrade_version)
            dest = Path(f"/tmp/{src.name}")
            self.node.put(dest, src)
            self.upgrade_version = str(dest)

    def test_snap_upgrade(self):
        """Test upgrade after install"""
        print(f"Install Version: {self.install_version}")
        print(f"Upgrade Version: {self.upgrade_version}")
        if self.upgrade_version.endswith(".snap"):
            self.node.snap.install(self.upgrade_version, classic=True, dangerous=True)
        else:
            self.node.snap.refresh("microk8s", channel=self.upgrade_version, classic=True)

    def test_restart_microk8s(self):
        """Test restarting microk8s"""
        self.node.microk8s.start()
        self.node.microk8s.wait_until_running(timeout=120)
        status = self.node.microk8s.status()
        assert "microk8s is running" in status

    def test_retest_addon(self, addon, input):
        """Retest addons"""
        self.test_addon(addon, input)


class TestXenialUpgrade(UpgradeTests):
    """Run Upgrade tests on a Xeinal node"""

    node_type = XenialLxd


class TestBionicUpgrade(UpgradeTests):
    """Run Upgrade tests on a Bionic node"""

    node_type = BionicLxd


class TestFocalUpgrade(UpgradeTests):
    """Run Upgrade tests on a Focal node"""

    node_type = FocalLxd
