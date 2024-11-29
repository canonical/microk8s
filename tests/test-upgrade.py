import os
import platform
import time
from validators import (
    validate_dns_dashboard,
    validate_storage,
    validate_ingress,
    validate_registry,
    validate_forward,
    validate_metrics_server,
    validate_metallb_config,
    validate_dual_stack,
)
from subprocess import check_call, CalledProcessError
from utils import (
    microk8s_enable,
    wait_for_pod_state,
    wait_for_installation,
    run_until_success,
    is_container,
    is_ipv6_configured,
    kubectl,
    _get_process,
)

upgrade_from = os.environ.get("UPGRADE_MICROK8S_FROM", "beta")
# Have UPGRADE_MICROK8S_TO point to a file to upgrade to that file
upgrade_to = os.environ.get("UPGRADE_MICROK8S_TO", "edge")
under_time_pressure = os.environ.get("UNDER_TIME_PRESSURE", "False")


class TestUpgrade(object):
    """
    Validates a microk8s upgrade path
    """

    def test_upgrade(self):
        """
        Deploy, probe, upgrade, validate nothing broke.

        """
        print("Testing upgrade from {} to {}".format(upgrade_from, upgrade_to))
        if is_ipv6_configured:
            print("IPv6 is configured, will test dual stack")
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
            lc_config_dir = "/var/snap/microk8s/common/"
            if not os.path.exists(lc_config_dir):
                os.makedirs(lc_config_dir)

            file_path = os.path.join(lc_config_dir, ".microk8s.yaml")
            with open(file_path, "w") as file:
                file.write(launch_config)

        cmd = "sudo snap install microk8s --classic --channel={}".format(upgrade_from)
        run_until_success(cmd)
        wait_for_installation()

        if is_ipv6_configured:
            kubectl("set env daemonset/calico-node -n kube-system IP=10.3.0.0/16 IP6=fd02::/64")

        # Run through the validators and
        # select those that were valid for the original snap
        test_matrix = {}
        try:
            enable = microk8s_enable("dns")
            wait_for_pod_state("", "kube-system", "running", label="k8s-app=kube-dns")
            assert "Nothing to do for" not in enable
            enable = microk8s_enable("dashboard")
            assert "Nothing to do for" not in enable
            validate_dns_dashboard()
            test_matrix["dns_dashboard"] = validate_dns_dashboard
        except CalledProcessError:
            print("Will not test dns-dashboard")

        try:
            enable = microk8s_enable("storage")
            assert "Nothing to do for" not in enable
            validate_storage()
            test_matrix["storage"] = validate_storage
        except CalledProcessError:
            print("Will not test storage")

        try:
            enable = microk8s_enable("ingress")
            assert "Nothing to do for" not in enable
            validate_ingress()
            test_matrix["ingress"] = validate_ingress
        except CalledProcessError:
            print("Will not test ingress")

        try:
            enable = microk8s_enable("registry")
            assert "Nothing to do for" not in enable
            validate_registry()
            test_matrix["registry"] = validate_registry
        except CalledProcessError:
            print("Will not test registry")

        try:
            validate_forward()
            test_matrix["forward"] = validate_forward
        except CalledProcessError:
            print("Will not test port forward")

        try:
            enable = microk8s_enable("metrics-server")
            assert "Nothing to do for" not in enable
            validate_metrics_server()
            test_matrix["metrics_server"] = validate_metrics_server
        except CalledProcessError:
            print("Will not test the metrics server")

        # AMD64 only tests
        if platform.machine() == "x86_64" and under_time_pressure == "False":
            try:
                ip_ranges = (
                    "192.168.0.105-192.168.0.105,192.168.0.110-192.168.0.111,192.168.1.240/28"
                )
                enable = microk8s_enable("{}:{}".format("metallb", ip_ranges), timeout_insec=500)
                assert "MetalLB is enabled" in enable and "Nothing to do for" not in enable
                validate_metallb_config(ip_ranges)
                test_matrix["metallb"] = validate_metallb_config
            except CalledProcessError:
                print("Will not test the metallb addon")

            if is_ipv6_configured:
                try:
                    validate_dual_stack()
                    test_matrix["dual_stack"] = validate_dual_stack
                except CalledProcessError:
                    print("Will not test the dual stack configuration")

        # Refresh the snap to the target
        if upgrade_to.endswith(".snap"):
            cmd = "sudo snap install {} --classic --dangerous".format(upgrade_to)
            run_until_success(cmd)
            cmd = "/snap/microk8s/current/connect-all-interfaces.sh"
            run_until_success(cmd)
            time.sleep(20)
        else:
            cmd = "sudo snap refresh microk8s --channel={}".format(upgrade_to)
            run_until_success(cmd)

        # Allow for the refresh to be processed
        time.sleep(10)
        wait_for_installation()

        # Test any validations that were valid for the original snap
        for test, validation in test_matrix.items():
            print("Testing {}".format(test))
            validation()

        if not is_container():
            # On lxc umount docker overlay is not permitted.
            check_call("sudo snap remove microk8s".split())
            coredns_procs = _get_process("coredns")
            assert len(coredns_procs) == 0, "Expected to have 0 coredns processes running."
