import requests
import os
import random
import string
import json
import shutil

BASE_URL = "https://127.0.0.1:25000/cluster/api/v1.0"
CALLBACK_TOKEN_FILE = "/var/snap/microk8s/current/credentials/callback-token.txt"


class TestClusterAgentApi(object):

    def test_version(self):
        """
        Test /version endpoint
        """
        token_value = self.get_or_generate_callback_token(CALLBACK_TOKEN_FILE)
        print("Token retrieved: {}".format(token_value))
        callback_json = {"callback": token_value}
        r = requests.post("{}/version".format(BASE_URL), json=callback_json, verify=False)
        assert r.status_code == 200, "Expecting 200 OK but {} received".format(r.status_code)
        print("MicroK8s version installed: {}".format(r.text))

    def test_status(self):
        """
        Test /status endpoint
        """
        token_value = self.get_or_generate_callback_token(CALLBACK_TOKEN_FILE)
        print("Token retrieved: {}".format(token_value))
        callback_json = {"callback": token_value}

        r = requests.post("{}/status".format(BASE_URL), json=callback_json, verify=False)
        assert r.status_code == 200, "Expecting 200 OK but {} received".format(r.status_code)
        is_valid_json = self.is_json(r.text)
        assert is_valid_json
        print("MicroK8s status: {}".format(r.text))
        print("Is valid json: {}".format(is_valid_json))

    def test_overview(self):
        """
        Test /overview endpoint
        """
        token_value = self.get_or_generate_callback_token(CALLBACK_TOKEN_FILE)
        print("Token retrieved: {}".format(token_value))
        callback_json = {"callback": token_value}

        r = requests.post("{}/overview".format(BASE_URL), json=callback_json, verify=False)
        assert r.status_code == 200, "Expecting 200 OK but {} received".format(r.status_code)
        assert r.text.strip(), "Empty response received"
        print("MicroK8s overview: {}".format(r.text))

    def test_services(self):
        """
        Test /services endpoint
        """
        token_value = self.get_or_generate_callback_token(CALLBACK_TOKEN_FILE)
        print("Token retrieved: {}".format(token_value))
        callback_json = {"callback": token_value}

        r = requests.post("{}/services".format(BASE_URL), json=callback_json, verify=False)
        assert r.status_code == 200, "Expecting 200 OK but {} received".format(r.status_code)
        is_valid_json = self.is_json(r.text)
        assert is_valid_json
        print("MicroK8s services: {}".format(r.text))
        print("Is valid json: {}".format(is_valid_json))

    def test_service_logs(self):
        """
        Test /service/logs endpoint
        """
        token_value = self.get_or_generate_callback_token(CALLBACK_TOKEN_FILE)
        print("Token retrieved: {}".format(token_value))
        callback_json = {"callback": token_value, "service": "microk8s.daemon-flanneld"}

        r = requests.post("{}/service/logs".format(BASE_URL), json=callback_json, verify=False)
        assert r.status_code == 200, "Expecting 200 OK but {} received".format(r.status_code)
        assert r.text.strip(), "Empty response received"
        print("microk8s.daemon-cluster-agent logs: {}".format(r.text))

    @staticmethod
    def get_or_generate_callback_token(callback_token_file):
        """
        Get token from file or generate a token and store it in the callback token file

        :return: the token
        """
        try:
            with open(callback_token_file) as f:
                token = f.read()
            if token.strip():
                return token
        except FileNotFoundError:
            # if file not found, continue
            pass

        token = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(64))
        with open(callback_token_file, "w") as fp:
            fp.write("{}\n".format(token))

        os.chmod(callback_token_file, 0o660)
        try:
            shutil.chown(callback_token_file, group='microk8s')
        except:
            # not setting the group means only the current user can access the file
            pass
        return token

    @staticmethod
    def is_json(myjson):
        try:
            json_object = json.loads(myjson)
        except ValueError as e:
            return False
        return True
