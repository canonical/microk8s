import pytest
import os
import time
import requests
from utils import (
    wait_for_installation,
    run_until_success,
)

upgrade_from = os.environ.get('UPGRADE_MICROK8S_FROM', 'beta')
# Have UPGRADE_MICROK8S_TO point to a file to upgrade to that file
upgrade_to = os.environ.get('UPGRADE_MICROK8S_TO', 'edge')


class TestUpgradePath:
    """
    Validates a microk8s upgrade path
    """

    @pytest.mark.skipif(
        os.environ.get('UNDER_TIME_PRESSURE') == 'True',
        reason="Skipping refresh path test as we are under time pressure",
    )
    def test_refresh_path(self):
        """
        Deploy an old snap and try to refresh until the current one.

        """
        start_channel = 16
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

        last_stable_minor -= 1

        print("")
        print(
            "Testing refresh path from 1.{} to 1.{} and finally refresh to {}".format(
                start_channel, last_stable_minor, upgrade_to
            )
        )
        assert last_stable_minor is not None

        channel = f"1.{start_channel}/stable"
        print(f"Installing {channel}")
        cmd = f"sudo snap install microk8s --classic --channel={channel}"
        run_until_success(cmd)
        wait_for_installation()
        channel_minor = start_channel
        channel_minor += 1
        while channel_minor <= last_stable_minor:
            channel = f"1.{channel_minor}/stable"
            print(f"Refreshing to {channel}")
            cmd = f"sudo snap refresh microk8s --classic --channel={channel}"
            run_until_success(cmd)
            wait_for_installation()
            time.sleep(30)
            channel_minor += 1

        print(f"Installing {upgrade_to}")
        if upgrade_to.endswith('.snap'):
            cmd = f"sudo snap install {upgrade_to} --classic --dangerous"
        else:
            cmd = f"sudo snap refresh microk8s --channel={upgrade_to}"
        run_until_success(cmd, timeout_insec=600)
        # Allow for the refresh to be processed
        time.sleep(20)
        wait_for_installation(timeout_insec=1200)
