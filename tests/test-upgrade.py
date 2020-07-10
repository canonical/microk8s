import pytest
import os
import platform
import time
import requests
from validators import (
    validate_dns_dashboard,
    validate_storage,
    validate_ingress,
    validate_ambassador,
    validate_gpu,
    validate_registry,
    validate_forward,
    validate_metrics_server,
    validate_prometheus,
    validate_fluentd,
    validate_jaeger,
    validate_kubeflow,
    validate_cilium,
    validate_multus,
)
from subprocess import check_call, CalledProcessError, check_output
from utils import (
    microk8s_enable,
    wait_for_pod_state,
    wait_for_installation,
    run_until_success,
)

upgrade_from = os.environ.get('UPGRADE_MICROK8S_FROM', 'beta')
# Have UPGRADE_MICROK8S_TO point to a file to upgrade to that file
upgrade_to = os.environ.get('UPGRADE_MICROK8S_TO', 'edge')
under_time_pressure = os.environ.get('UNDER_TIME_PRESSURE', 'False')


class TestUpgrade(object):
    """
    Validates a microk8s upgrade path
    """

    @pytest.mark.skipif(
        os.environ.get('UNDER_TIME_PRESSURE') == 'True',
        reason="Skipping refresh path tast as we are under time pressure",
    )
    def test_refresh_path(self):
        """
        Deploy an old snap and try to refresh until the current one.

        """
        start_channel = 14

        last_stable_minor = None
        if upgrade_from.startswith('latest') or '/' not in upgrade_from:
            attempt = 0
            release_url = "https://dl.k8s.io/release/stable.txt"
            while attempt < 10 and not last_stable_minor:
                r = requests.get(release_url)
                if r.status_code == 200:
                    last_stable_str = r.content.decode().strip()
                    # We have "v1.18.4" and we need the "18"
                    last_stable_parts = last_stable_str.split('.')
                    last_stable_minor = int(last_stable_parts[1])
                else:
                    time.sleep(3)
                    attempt += 1
        else:
            channel_parts = upgrade_from.split('.')
            channel_parts = channel_parts[1].split('/')
            print(channel_parts)
            last_stable_minor = int(channel_parts[0])

        print("")
        print(
            "Testing refresh path from 1.{} to 1.{} and finally refresh to {}".format(
                start_channel, last_stable_minor, upgrade_to
            )
        )
        assert last_stable_minor is not None

        channel = "1.{}/stable".format(start_channel)
        print("Installing {}".format(channel))
        cmd = "sudo snap install microk8s --classic --channel={}".format(channel)
        run_until_success(cmd)
        wait_for_installation()
        channel_minor = start_channel
        channel_minor += 1
        while channel_minor <= last_stable_minor:
            channel = "1.{}/stable".format(channel_minor)
            print("Refreshing to {}".format(channel))
            cmd = "sudo snap refresh microk8s --classic --channel={}".format(channel)
            run_until_success(cmd)
            wait_for_installation()
            channel_minor += 1

        print("Installing {}".format(upgrade_to))
        if upgrade_to.endswith('.snap'):
            cmd = "sudo snap install {} --classic --dangerous".format(upgrade_to)
        else:
            cmd = "sudo snap refresh microk8s --channel={}".format(upgrade_to)
        run_until_success(cmd)
        # Allow for the refresh to be processed
        time.sleep(10)
        wait_for_installation()

    def test_upgrade(self):
        """
        Deploy, probe, upgrade, validate nothing broke.

        """
        print("Testing upgrade from {} to {}".format(upgrade_from, upgrade_to))

        cmd = "sudo snap install microk8s --classic --channel={}".format(upgrade_from)
        run_until_success(cmd)
        wait_for_installation()
        if is_container():
            # In some setups (eg LXC on GCE) the hashsize nf_conntrack file under
            # sys is marked as rw but any update on it is failing causing kube-proxy
            # to fail.
            here = os.path.dirname(os.path.abspath(__file__))
            apply_patch = os.path.join(here, "patch-kube-proxy.sh")
            check_call("sudo {}".format(apply_patch).split())

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
            test_matrix['dns_dashboard'] = validate_dns_dashboard
        except:
            print('Will not test dns-dashboard')

        try:
            enable = microk8s_enable("storage")
            assert "Nothing to do for" not in enable
            validate_storage()
            test_matrix['storage'] = validate_storage
        except:
            print('Will not test storage')

        try:
            enable = microk8s_enable("ingress")
            assert "Nothing to do for" not in enable
            validate_ingress()
            test_matrix['ingress'] = validate_ingress
        except:
            print('Will not test ingress')

        try:
            enable = microk8s_enable("gpu")
            assert "Nothing to do for" not in enable
            validate_gpu()
            test_matrix['gpu'] = validate_gpu
        except:
            print('Will not test gpu')

        try:
            enable = microk8s_enable("registry")
            assert "Nothing to do for" not in enable
            validate_registry()
            test_matrix['registry'] = validate_registry
        except:
            print('Will not test registry')

        try:
            validate_forward()
            test_matrix['forward'] = validate_forward
        except:
            print('Will not test port forward')

        try:
            enable = microk8s_enable("metrics-server")
            assert "Nothing to do for" not in enable
            validate_metrics_server()
            test_matrix['metrics_server'] = validate_metrics_server
        except:
            print('Will not test the metrics server')

        # AMD64 only tests
        if platform.machine() == 'x86_64' and under_time_pressure == 'False':
            '''
            # Prometheus operator on our lxc is chashlooping disabling the test for now.
            try:
                enable = microk8s_enable("prometheus", timeout_insec=30)
                assert "Nothing to do for" not in enable
                validate_prometheus()
                test_matrix['prometheus'] = validate_prometheus
            except:
                print('Will not test the prometheus')

            # The kubeflow deployment is huge. It will not fit comfortably
            # with the rest of the addons on the same machine during an upgrade
            # we will need to find another way to test it.
            try:
                enable = microk8s_enable("kubeflow", timeout_insec=30)
                assert "Nothing to do for" not in enable
                validate_kubeflow()
                test_matrix['kubeflow'] = validate_kubeflow
            except:
                print('Will not test kubeflow')
            '''

            try:
                enable = microk8s_enable("fluentd", timeout_insec=30)
                assert "Nothing to do for" not in enable
                validate_fluentd()
                test_matrix['fluentd'] = validate_fluentd
            except:
                print('Will not test the fluentd')

            try:
                enable = microk8s_enable("jaeger", timeout_insec=30)
                assert "Nothing to do for" not in enable
                validate_jaeger()
                test_matrix['jaeger'] = validate_jaeger
            except:
                print('Will not test the jaeger addon')

            try:
                enable = microk8s_enable("cilium", timeout_insec=300)
                assert "Nothing to do for" not in enable
                validate_cilium()
                test_matrix['cilium'] = validate_cilium
            except:
                print('Will not test the cilium addon')

            try:
                enable = microk8s_enable("multus", timeout_insec=150)
                assert "Nothing to do for" not in enable
                validate_multus()
                test_matrix['multus'] = validate_multus
            except:
                print('Will not test the multus addon')

        # Refresh the snap to the target
        if upgrade_to.endswith('.snap'):
            cmd = "sudo snap install {} --classic --dangerous".format(upgrade_to)
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


def is_container():
    '''
    Returns: True if the deployment is in a VM/container.

    '''
    try:
        if os.path.isdir('/run/systemd/system'):
            container = check_output('sudo systemd-detect-virt --container'.split())
            print("Tests are running in {}".format(container))
            return True
    except CalledProcessError:
        print("systemd-detect-virt did not detect a container")

    if os.path.exists('/run/container_type'):
        return True

    try:
        check_call("sudo grep -E (lxc|hypervisor) /proc/1/environ /proc/cpuinfo".split())
        print("Tests are running in an undetectable container")
        return True
    except CalledProcessError:
        print("no indication of a container in /proc")

    return False
