from validators import validate_dns, validate_dashboard, validate_storage
from utils import microk8s_enable, wait_for_pod_state, microk8s_disable
from subprocess import Popen, PIPE, STDOUT

class TestAddons(object):

    def test_dns(self):
        """
        Sets up DNS addon and validates it works.

        """
        print("Enabling DNS")
        microk8s_enable("dns")
        wait_for_pod_state("", "kube-system", "running", label="k8s-app=kube-dns")
        # Create a bbox
        print("Validating dns")
        validate_dns()
        print("Disabling DNS")
        microk8s_disable("dns")

    def test_dashboard(self):
        """
        Sets up dashboard and validates it works.

        """
        print("Enabling DNS")
        microk8s_enable("dns")
        wait_for_pod_state("", "kube-system", "running", label="k8s-app=kube-dns")
        print("Enabling dashboard")
        microk8s_enable("dashboard")
        print("Validating dashboard")
        validate_dashboard()
        print("Disabling DNS")
        microk8s_disable("dns")
        print("Disabling dashboard")
        microk8s_disable("dashboard")

    def test_storage(self):
        """
        Sets up storage addon and validates it works.

        """
        print("Enabling storage")
        microk8s_enable("storage")
        print("Validating storage")
        validate_storage()
        print("Disabling storage")
        p = Popen("/snap/bin/microk8s.disable storage".split(), stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        disable = p.communicate(input=b'Y')[0]

    def test_ingress(self):
        """
        Sets up ingress addon and validates it works.

        """
        print("Enabling ingress")
        microk8s_enable("ingress")
        print("Validating ingress")
        validate_ingress()
        print("Disabling ingress")
        microk8s_disable("ingress")
