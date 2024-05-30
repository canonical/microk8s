import requests


class TestClusterAgent(object):
    """
    Validates the cluster agent in MicroK8s
    """

    def test_cluster_agent_health(self):
        """
        Query the cluster agent health endpoint to verify it is up and healthy.

        """
        response = requests.get(
            "https://127.0.0.1:25000/health", verify="/var/snap/microk8s/current/certs/ca.crt"
        )
        assert response.status_code == 200 and response.json()["status"] == "OK"
