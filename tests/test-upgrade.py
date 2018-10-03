import os
import time
from validators import validate_dns, validate_dashboard, validate_storage, validate_ingress
from subprocess import check_call, CalledProcessError, call
from utils import microk8s_enable, wait_for_pod_state, microk8s_disable, wait_for_installation

upgrade_from = os.environ.get('UPGRADE_MICROK8S_FROM', 'beta')
# Have UPGRADE_MICROK8S_TO point to a file to upgrade to that file
upgrade_to = os.environ.get('UPGRADE_MICROK8S_TO', 'edge')


class TestUpgrade(object):
    """
    Validates a microk8s upgrade path
    """

    def test_upgrade(self):
        """
        Deploy, probe, upgrade, validate nothing broke.

        """
        print("Testing upgrade from {} to {}".format(upgrade_from, upgrade_to))

        cmd = "sudo snap install microk8s --classic --channel={}".format(upgrade_from).split()
        check_call(cmd)
        wait_for_installation()
        if is_container():
            # In some setups (eg LXC on GCE) the hashsize nf_conntrack file under
            # sys is marked as rw but any update on it is failing causing kube-proxy
            # to fail. So we call path-kube-proxy, which will tell kube-proxy to not use conntrack.
            here = os.path.dirname(os.path.abspath(__file__))
            apply_patch = os.path.join(here, "patch-kube-proxy.sh")
            check_call("sudo {}".format(apply_patch).split())

        # Run through the validators and
        # select those that were valid for the original snap
        test_matrix = {}
        try:
            microk8s_enable("dns")
            wait_for_pod_state("", "kube-system", "running", label="k8s-app=kube-dns")
            validate_dns()
            test_matrix['dns'] = validate_dns
        except:
            print('Will not test dns')

        try:
            microk8s_enable("dashboard")
            validate_dashboard()
            test_matrix['dashboard'] = validate_dashboard
        except:
            print('Will not test dashboard')

        try:
            microk8s_enable("storage")
            validate_storage()
            test_matrix['storage'] = validate_storage
        except:
            print('Will not test storage')

        try:
            microk8s_enable("ingress")
            validate_ingress()
            test_matrix['ingress'] = validate_ingress
        except:
            print('Will not test ingress')

        # Refresh the snap to the target
        if upgrade_to.endswith('.snap'):
            cmd = "sudo snap install {} --classic --dangerous".format(upgrade_to).split()
        else:
            cmd = "sudo snap refresh microk8s --channel={}".format(upgrade_to).split()
        check_call(cmd)
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
            return (call(['sudo', 'systemd-detect-virt', '--container']) == 0)
        else:
            return os.path.exists('/run/container_type')
    except CalledProcessError:
        return False
