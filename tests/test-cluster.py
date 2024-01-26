import string
import random
import time
import pytest
import os
import datetime
import requests
import signal
import subprocess
from os import path
from pathlib import Path
from utils import (
    is_strict,
    is_ipv6_configured,
)


# Provide a list of VMs you want to reuse. VMs should have already microk8s installed.
# the test will attempt a refresh to the channel requested for testing
# reuse_vms = ['vm-ldzcjb', 'vm-nfpgea', 'vm-pkgbtw']
reuse_vms = None

# Channel we want to test. A full path to a local snap can be used for local builds
channel_to_test = os.environ.get("CHANNEL_TO_TEST", "latest/stable")
backend = os.environ.get("BACKEND", None)
profile = os.environ.get("LXC_PROFILE", "lxc/microk8s.profile")
snap_data = os.environ.get("SNAP_DATA", "/var/snap/microk8s/current")

TEMPLATES = Path(__file__).absolute().parent / "templates"


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

    def __init__(self, backend=None, attach_vm=None):
        """Detect the available backends and instantiate a VM.

        If `attach_vm` is provided we just make sure the right MicroK8s is deployed.
        :param backend: either multipass of lxc
        :param attach_vm: the name of the VM we want to reuse
        """
        rnd_letters = "".join(random.choice(string.ascii_lowercase) for i in range(6))
        self.backend = backend
        self.vm_name = "vm-{}".format(rnd_letters)
        self.attached = False
        if attach_vm:
            self.attached = True
            self.vm_name = attach_vm

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
                "/snap/bin/multipass exec {}  -- sudo " "{}".format(self.vm_name, cmd).split()
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


class TestCluster(object):
    @pytest.fixture(autouse=True, scope="module")
    def setup_cluster(self):
        """
        Provision VMs and for a cluster.
        :return:
        """
        try:
            print("Setting up cluster")
            type(self).VM = []
            if not reuse_vms:
                size = 3
                for i in range(0, size):
                    print("Creating machine {}".format(i))
                    vm = VM(backend)
                    vm.setup(channel_to_test)
                    print("Waiting for machine {}".format(i))
                    vm.run("/snap/bin/microk8s.status --wait-ready --timeout 120")
                    self.VM.append(vm)
            else:
                for vm_name in reuse_vms:
                    vm = VM(backend, vm_name)
                    vm.setup(channel_to_test)
                    self.VM.append(vm)

            # Form cluster
            vm_master = self.VM[0]
            connected_nodes = vm_master.run("/snap/bin/microk8s.kubectl get no")
            for vm in self.VM:
                if vm.vm_name in connected_nodes.decode():
                    continue
                else:
                    print("Adding machine {} to cluster".format(vm.vm_name))
                    add_node = vm_master.run("/snap/bin/microk8s.add-node")
                    endpoint = [ep for ep in add_node.decode().split() if ":25000/" in ep]
                    vm.run("/snap/bin/microk8s.join {}".format(endpoint[0]))

            # Wait for nodes to be ready
            print("Waiting for nodes to register")
            attempt = 0
            while attempt < 10:
                try:
                    connected_nodes = vm_master.run("/snap/bin/microk8s.kubectl get no")
                    if "NotReady" in connected_nodes.decode():
                        time.sleep(5)
                    connected_nodes = vm_master.run("/snap/bin/microk8s.kubectl get no")
                    print(connected_nodes.decode())
                    break
                except ChildProcessError:
                    time.sleep(10)
                    attempt += 1
                    if attempt == 10:
                        raise

            # Wait for CNI pods
            print("Waiting for cni")
            while True:
                ready_pods = 0
                pods = vm_master.run("/snap/bin/microk8s.kubectl get po -n kube-system -o wide")
                for line in pods.decode().splitlines():
                    if "calico" in line and "Running" in line:
                        ready_pods += 1
                if ready_pods == (len(self.VM) + 1):
                    print(pods.decode())
                    break
                time.sleep(5)

            yield

        finally:
            print("Cleanup up cluster")
            if not reuse_vms:
                for vm in self.VM:
                    print("Releasing machine {} in {}".format(vm.vm_name, vm.backend))
                    vm.release()

    def test_calico_in_nodes(self):
        """
        Test each node has a calico pod.
        """
        print("Checking calico is in all nodes")
        pods = self.VM[0].run("/snap/bin/microk8s.kubectl get po -n kube-system -o wide")
        for vm in self.VM:
            if vm.vm_name not in pods.decode():
                assert False
            print("Calico found in node {}".format(vm.vm_name))

    @pytest.mark.skipif(
        is_strict(),
        reason="Skipping because calico interfaces are not removed on strict",
    )
    def test_calico_interfaces_removed_on_snap_remove(self):
        """
        Test that calico interfaces are not present on the node
        when the microk8s snap is removed.
        """
        vm = VM(backend)
        vm.setup(channel_to_test)
        print("Waiting for machine {}".format(vm.vm_name))
        vm.run("/snap/bin/microk8s.status --wait-ready --timeout 240")
        timeout = time.time() + 240
        ready = False
        while time.time() <= timeout and not ready:
            try:
                pods = vm.run("/snap/bin/microk8s.kubectl get po -n kube-system -o wide")
                for line in pods.decode().splitlines():
                    if "calico" in line and "Running" in line:
                        ready = True
            except ChildProcessError:
                print("Waiting for k8s pods to come up")
            time.sleep(5)
        assert ready
        vm.run("snap remove --purge microk8s")
        interfaces = vm.run("/sbin/ip a")
        assert "cali" not in interfaces.decode()
        vm.release()

    def test_nodes_in_ha(self):
        """
        Test all nodes are seeing the database while removing nodes
        """
        # All nodes see the same pods
        for vm in self.VM:
            pods = vm.run("/snap/bin/microk8s.kubectl get po -n kube-system -o wide")
            for other_vm in self.VM:
                if other_vm.vm_name not in pods.decode():
                    assert False
        print("All nodes see the same pods")

        attempt = 100
        while True:
            assert attempt > 0
            for vm in self.VM:
                status = vm.run("/snap/bin/microk8s.status")
                if "high-availability: yes" not in status.decode():
                    attempt += 1
                    continue
            break

        # remove a node
        print("Removing machine {}".format(self.VM[0].vm_name))
        self.VM[0].run("/snap/bin/microk8s.leave")
        self.VM[1].run("/snap/bin/microk8s.remove-node {}".format(self.VM[0].vm_name))
        # allow for some time for the leader to hand over leadership
        time.sleep(10)
        attempt = 100
        while True:
            ready_pods = 0
            pods = self.VM[1].run("/snap/bin/microk8s.kubectl get po -n kube-system -o wide")
            for line in pods.decode().splitlines():
                if "calico" in line and "Running" in line:
                    ready_pods += 1
            if ready_pods == (len(self.VM)):
                print(pods.decode())
                break
            attempt -= 1
            if attempt <= 0:
                assert False
            time.sleep(5)
        print("Checking calico is on the nodes running")

        leftVMs = [self.VM[1], self.VM[2]]
        attempt = 100
        while True:
            assert attempt > 0
            for vm in leftVMs:
                status = vm.run("/snap/bin/microk8s.status")
                if "high-availability: no" not in status.decode():
                    attempt += 1
                    time.sleep(2)
                    continue
            break

        for vm in leftVMs:
            pods = vm.run("/snap/bin/microk8s.kubectl get po -n kube-system -o wide")
            for other_vm in leftVMs:
                if other_vm.vm_name not in pods.decode():
                    time.sleep(2)
                    assert False
        print("Remaining nodes see the same pods")

        print("Waiting for two ingress to appear")
        self.VM[1].run("/snap/bin/microk8s.enable ingress")
        # wait for two ingress to appear
        time.sleep(10)
        attempt = 100
        while True:
            ready_pods = 0
            pods = self.VM[1].run("/snap/bin/microk8s.kubectl get po -A -o wide")
            for line in pods.decode().splitlines():
                if "ingress" in line and "Running" in line:
                    ready_pods += 1
            if ready_pods == (len(self.VM) - 1):
                print(pods.decode())
                break
            attempt -= 1
            if attempt <= 0:
                assert False
            time.sleep(5)

        print("Rejoin the node")
        add_node = self.VM[1].run("/snap/bin/microk8s.add-node")
        endpoint = [ep for ep in add_node.decode().split() if ":25000/" in ep]
        self.VM[0].run("/snap/bin/microk8s.join {}".format(endpoint[0]))

        print("Waiting for nodes to be ready")
        attempt = 0
        while attempt < 10:
            try:
                connected_nodes = self.VM[0].run("/snap/bin/microk8s.kubectl get no")
                if "NotReady" in connected_nodes.decode():
                    time.sleep(5)
                    continue
                print(connected_nodes.decode())
                break
            except ChildProcessError:
                time.sleep(10)
                attempt += 1
                if attempt == 10:
                    raise

        attempt = 100
        while True:
            assert attempt > 0
            for vm in self.VM:
                status = vm.run("/snap/bin/microk8s.status")
                if "high-availability: yes" not in status.decode():
                    attempt += 1
                    time.sleep(2)
                    continue
            break

    def test_worker_node(self):
        """
        Test a worker node is setup
        """
        print("Setting up a worker node")
        vm = VM(backend)
        vm.setup(channel_to_test)
        self.VM.append(vm)

        # Form cluster
        vm_master = self.VM[0]
        print("Adding machine {} to cluster".format(vm.vm_name))
        add_node = vm_master.run("/snap/bin/microk8s.add-node")
        endpoint = [ep for ep in add_node.decode().split() if ":25000/" in ep]
        vm.run("/snap/bin/microk8s.join {} --worker".format(endpoint[0]))
        ep_parts = endpoint[0].split(":")
        master_ip = ep_parts[0]

        # Wait for nodes to be ready
        print("Waiting for node to register")
        attempt = 0
        while attempt < 10:
            try:
                connected_nodes = vm_master.run("/snap/bin/microk8s.kubectl get no")
                if (
                    "NotReady" in connected_nodes.decode()
                    or vm.vm_name not in connected_nodes.decode()
                ):
                    time.sleep(5)
                    continue
                print(connected_nodes.decode())
                break
            except ChildProcessError:
                time.sleep(10)
                attempt += 1
                if attempt == 10:
                    raise

        # Check that kubelet talks to the control plane node via the local proxy
        print("Checking the worker's configuration")
        provider = vm.run("cat /var/snap/microk8s/current/args/traefik/provider.yaml")
        assert master_ip in provider.decode()
        kubelet = vm.run("cat /var/snap/microk8s/current/credentials/kubelet.config")
        assert "127.0.0.1" in kubelet.decode()

        # Leave the worker node from the cluster
        print("Leaving the worker node {} from the cluster".format(vm.vm_name))
        vm.run("/snap/bin/microk8s.leave")
        vm_master.run("/snap/bin/microk8s.remove-node {}".format(vm.vm_name))

        # Wait for worker node to leave the cluster
        attempt = 0
        while attempt < 10:
            try:
                connected_nodes = vm_master.run("/snap/bin/microk8s.kubectl get no")
                print(connected_nodes.decode())
                if "NotReady" in connected_nodes.decode() or vm.vm_name in connected_nodes.decode():
                    time.sleep(5)
                    continue
                print(connected_nodes.decode())
                break
            except ChildProcessError:
                time.sleep(10)
                attempt += 1
                if attempt == 10:
                    raise

        # Check that the worker node is Ready
        print("Checking that the worker node {} is working and Ready".format(vm.vm_name))
        worker_node = vm.run("/snap/bin/microk8s status --wait-ready")
        print(worker_node.decode())
        assert "microk8s is running" in worker_node.decode()

        # The removed node now isn't part of the cluster and will re-issue certificates.
        # This will interfere when testing `test_no_cert_reissue_in_nodes`.
        # Hence, we remove this machine from the VM list.
        print("Remove machine {}".format(vm.vm_name))
        self.VM.remove(vm)
        vm.release()

    def test_no_cert_reissue_in_nodes(self):
        """
        Test that each node has the cert no-reissue lock.
        """
        print("Checking for the no re-issue lock")
        for vm in self.VM:
            lock_files = vm.run("ls /var/snap/microk8s/current/var/lock/")
            assert "no-cert-reissue" in lock_files.decode()

    @pytest.mark.skipif(
        # If the host system does not have IPv6 support or is not configured for IPv6,
        # it won't be able to create VMs with IPv6 connectivity.
        not is_ipv6_configured,
        reason="Skipping dual stack tests on VMs which are not lxc based and not dual-stack enabled",
    )
    def test_dual_stack_cluster(self):
        vm = self.VM[0]
        # Deploy the test deployment and service
        manifest = TEMPLATES / "dual-stack.yaml"
        remote_path = "{}/tmp/dual-stack.yaml".format(snap_data)
        vm.transfer_file(manifest, remote_path)
        vm.run("ls -al {}".format(remote_path))
        vm.run("/snap/bin/microk8s.kubectl apply -f {}".format(remote_path))

        # Wait for the deployment to become ready
        print("Waiting for nginx deployment")
        while True:
            ready_pods = 0
            pods = vm.run("/snap/bin/microk8s.kubectl get po -o wide")
            for line in pods.decode().splitlines():
                if "nginxdualstack" in line and "Running" in line:
                    ready_pods = 1
            if ready_pods == 1:
                print(pods.decode())
                break
            time.sleep(5)

        # ping the service attached with the deployment
        ep = (
            "/snap/bin/microk8s.kubectl get service nginx6 "
            "-o jsonpath='{.spec.clusterIP}' --output='jsonpath=['{.spec.clusterIP}']'"
        )
        ipv6_endpoint = vm.run(ep).decode()
        print("Pinging endpoint: http://{}/".format(ipv6_endpoint))
        url = f"http://{ipv6_endpoint}/"
        attempt = 10
        while attempt >= 0:
            try:
                resp = vm.run("curl {}".format(url))
                if "Kubernetes IPv6 nginx" in resp.decode():
                    print(resp)
                    break
            except subprocess.CalledProcessError as e:
                print("Error occurred during the request:", str(e))
                raise
            attempt -= 1
            time.sleep(2)


class TestUpgradeCluster(object):
    @pytest.fixture(autouse=True, scope="module")
    def setup_old_versioned_cluster(self):
        """
        Provision VMs of the previous version and form the cluster.
        """
        try:
            print("Setting up cluster of an older version")
            if channel_to_test.startswith("latest") or "/" not in channel_to_test:
                attempt = 0
                release_url = "https://dl.k8s.io/release/stable.txt"
                while attempt < 10:
                    try:
                        r = requests.get(release_url)
                        if r.status_code == 200:
                            last_stable_str = r.content.decode().strip()
                            last_stable_str = last_stable_str.replace("v", "")
                            last_stable_str = ".".join(last_stable_str.split(".")[:2])
                            break
                    except TimeoutError:
                        time.sleep(3)
                        attempt += 1
                        if attempt == 10:
                            raise

            track, *_ = channel_to_test.split("/")
            if track == "latest":
                track = last_stable_str

            # For eksd and stable tracks, we need a previous version on these tracks.
            # Eg, to test 1.24-eksd, we need 1.23-eksd track.
            major = track.split(".")[0]
            minor = track.split(".")[1].split("-")[0]
            branch = track.split("-")[1] if len(track.split("-")) > 1 else ""

            if minor == "0" and major >= "1":
                major = str(int(major) - 1)
                minor = "9"
            else:
                if "-" in track:
                    minor = str(int(minor.split("-")[0]) - 1)
                else:
                    minor = str(int(minor) - 1)

            branch = "-" + branch if branch != "" else ""
            older_version = major + "." + minor + branch + "/" + "stable"
            print("Old version is {}".format(older_version))

            type(self).VM = []
            if not reuse_vms:
                print("Creating machine")
                vm = VM(backend)
                vm.setup(older_version)
                print("Waiting for machine")
                vm.run("/snap/bin/microk8s.status --wait-ready --timeout 120")
                self.VM.append(vm)
            else:
                vm = VM(backend, reuse_vms[0])
                vm.setup(older_version)
                self.VM.append(vm)

            vm_older_version = self.VM[0]

            # Wait for CNI pods
            print("Waiting for cni")
            while True:
                ready_pods = 0
                attempt = 0
                try:
                    pods = vm_older_version.run(
                        "/snap/bin/microk8s.kubectl get po -n kube-system -o wide"
                    )
                    for line in pods.decode().splitlines():
                        if "calico" in line and "Running" in line:
                            ready_pods += 1
                    if ready_pods == (len(self.VM) + 1):
                        print(pods.decode())
                        break
                    time.sleep(5)
                except ChildProcessError:
                    time.sleep(10)
                    attempt += 1
                    if attempt == 10:
                        raise
                time.sleep(5)
            yield

        finally:
            print("Cleanup up cluster")
            if not reuse_vms:
                for vm in self.VM:
                    print("Releasing machine {} in {}".format(vm.vm_name, vm.backend))
                    vm.release()

    @pytest.mark.skipif(
        is_strict() and backend == "lxc",
        reason="Skipping test of multi-version cluster on strict and lxc",
    )
    def test_mixed_version_join(self):
        """
        Test n versioned node joining a n-1 versioned cluster.
        """
        print("Setting up an newer versioned node")
        vm = VM(backend)
        vm.setup(channel_to_test)
        self.VM.append(vm)

        # Form cluster
        vm_older_version = self.VM[0]
        print("Adding newer versioned machine {} to cluster".format(vm.vm_name))
        add_node = vm_older_version.run("/snap/bin/microk8s.add-node")
        endpoint = [ep for ep in add_node.decode().split() if ":25000/" in ep]
        vm.run("/snap/bin/microk8s.join {}".format(endpoint[0]))

        # Wait for nodes to be ready
        print("Waiting for two node to be Ready")
        attempt = 0
        timeout_insec = 300
        deadline = datetime.datetime.now() + datetime.timedelta(seconds=timeout_insec)
        while attempt < 10:
            try:
                # Timeout after few minutes.
                if datetime.datetime.now() > deadline:
                    raise TimeoutError(
                        "Nodes not in Ready state after {} seconds.".format(timeout_insec)
                    )

                connected_nodes = vm_older_version.run("/snap/bin/microk8s.kubectl get no")
                num_nodes = connected_nodes.count(b" Ready")
                if num_nodes != 2:
                    time.sleep(5)
                    continue
                print(connected_nodes.decode())
                break
            except ChildProcessError:
                time.sleep(10)
                attempt += 1
                if attempt == 10:
                    raise
