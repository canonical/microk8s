from pathlib import Path
from vm import VM

import os
import pytest
import time

# Provide a list of VMs you want to reuse. VMs should have already microk8s installed.
# the test will attempt a refresh to the channel requested for testing
# reuse_vms = ['vm-ldzcjb', 'vm-nfpgea', 'vm-pkgbtw']
reuse_vms = None

# Channel we want to test. A full path to a local snap can be used for local builds
channel_to_test = (
    "latest/edge/intermediate-ca"  # os.environ.get("CHANNEL_TO_TEST", "latest/stable")
)
backend = os.environ.get("BACKEND", None)
snap_data = os.environ.get("SNAP_DATA", "/var/snap/microk8s/current")

CREATE_INTERMEDIATE_CA_SCRIPT_NAME = "create-intermediate-ca.sh"
CREATE_INTERMEDIATE_CA_PATH = Path(__file__).absolute().parent / "libs/intermediate-ca"


class TestIntermediateCA:
    @pytest.fixture(autouse=True, scope="module")
    def setup_vms(self):
        """
        Provision VMs for a cluster.
        :return:
        """
        try:
            print("Setting up VMs")
            type(self).VM = []
            if not reuse_vms:
                size = 2
                for i in range(0, size):
                    print("Creating machine {}".format(i))
                    vm = VM(backend, enable_ipv6=False)
                    vm.setup(channel_to_test)
                    print("Waiting for machine {}".format(i))
                    vm.run("/snap/bin/microk8s.status --wait-ready --timeout 120")
                    self.VM.append(vm)

                    print("Waiting for cni")
                    while True:
                        ready_pods = 0
                        pods = vm.run("/snap/bin/microk8s.kubectl get po -n kube-system -o wide")
                        for line in pods.decode().splitlines():
                            if "calico" in line and "Running" in line:
                                ready_pods += 1
                        if ready_pods == (len(self.VM) + 1):
                            print(pods.decode())
                            break
                        time.sleep(5)

                    print("Everything up")

            else:
                for vm_name in reuse_vms:
                    vm = VM(backend, vm_name)
                    vm.setup(channel_to_test)
                    self.VM.append(vm)

            yield
        finally:
            print("Cleanup up VMs")
            if not reuse_vms:
                for vm in self.VM:
                    print("Releasing machine {} in {}".format(vm.vm_name, vm.backend))
                    vm.release()

    def create_intermediate_ca(self):
        vm: VM = self.VM[0]

        print("Transfer script")
        vm.transfer_file(f"{CREATE_INTERMEDIATE_CA_PATH}/create-intermediate-ca.sh", ".")
        vm.transfer_file(f"{CREATE_INTERMEDIATE_CA_PATH}/root-openssl-template.cnf", ".")
        vm.transfer_file(f"{CREATE_INTERMEDIATE_CA_PATH}/intermediate-openssl-template.cnf", ".")

        print("Make executable")
        vm.run(f"chmod 775 {CREATE_INTERMEDIATE_CA_SCRIPT_NAME}")
        print("Run")
        vm.run(f"./{CREATE_INTERMEDIATE_CA_SCRIPT_NAME}")
        print("Done")

    def test_services_come_up(self):
        vm: VM = self.VM[0]

        self.create_intermediate_ca()

        print("Refresh certificates to use intermediate CA")
        vm.run("microk8s refresh-certs /home/ubuntu/certs/microk8s-certs")

        output = vm.run("microk8s kubectl get nodes")
        # Split the output into lines and skip the header
        lines = output.decode("utf-8").split("\n")[1:]

        # Iterate through the lines to check the node status
        for line in lines:
            # Split the line by whitespace
            parts = line.split()
            # Check if the node status is "Ready"
            if len(parts) > 1 and parts[1] != "Ready":
                # If any node is not in "Ready" status, fail the test
                assert False, f"Node {parts[0]} is not in Ready status"

        print("All nodes ready")

        print("Restart calico to pick up the new CA.")
        vm.run("microk8s kubectl rollout restart ds/calico-node -n kube-system")
        print("Wait for Calico to come up again.")
        while True:
            ready_pods = 0
            pods = vm.run("/snap/bin/microk8s.kubectl get po -n kube-system -o wide")
            for line in pods.decode().splitlines():
                if "calico" in line and "Running" in line:
                    ready_pods += 1
            if ready_pods == (len(self.VM) + 1):
                print(pods.decode())
                break
            time.sleep(5)

        print("Done")

    def test_join_node(self):
        # Form cluster
        vm_master = self.VM[0]
        vm_slave = self.VM[1]

        print("Adding machine {} to cluster".format(vm_slave.vm_name))
        add_node = vm_master.run("/snap/bin/microk8s.add-node")
        endpoint = [ep for ep in add_node.decode().split() if ":25000/" in ep]
        vm_slave.run("/snap/bin/microk8s.join {} --worker".format(endpoint[0]))

        # Wait for nodes to be ready
        print("Waiting for node to register")
        attempt = 0
        while attempt < 10:
            try:
                connected_nodes = vm_master.run("/snap/bin/microk8s.kubectl get no")
                if (
                    "NotReady" in connected_nodes.decode()
                    or vm_slave.vm_name not in connected_nodes.decode()
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
