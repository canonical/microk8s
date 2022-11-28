import pytest
import os
import time
import requests
from utils import (
    wait_for_installation,
    run_until_success,
)

upgrade_from = os.environ.get("UPGRADE_MICROK8S_FROM", "beta")
# Have UPGRADE_MICROK8S_TO point to a file to upgrade to that file
upgrade_to = os.environ.get("UPGRADE_MICROK8S_TO", "edge")


class TestUpgradePath(object):
    """
    Validates a microk8s upgrade path
    """

    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping refresh path test as we are under time pressure",
    )
    def test_refresh_path(self):
        """
        Deploy an old snap and try to refresh until the current one.

        """
        start_channel = 22
        last_stable_minor = 22

        print("")
        print(
            "Testing refresh path from 1.{} to 1.{} and finally refresh to {}".format(
                start_channel, last_stable_minor, upgrade_to
            )
        )
        assert last_stable_minor is not None

        channel = "1.{}-eksd/stable".format(start_channel)
        print("Installing {}".format(channel))
        cmd = "sudo snap install microk8s --classic --channel={}".format(channel)
        run_until_success(cmd)
        wait_for_installation()
        channel_minor = start_channel
        channel_minor += 1
        while channel_minor <= last_stable_minor:
            channel = "1.{}-eksd/stable".format(channel_minor)
            print("Refreshing to {}".format(channel))
            cmd = "sudo snap refresh microk8s --classic --channel={}".format(channel)
            run_until_success(cmd)
            wait_for_installation()
            time.sleep(30)
            channel_minor += 1

        print("Installing {}".format(upgrade_to))
        if upgrade_to.endswith(".snap"):
            cmd = "sudo snap install {} --classic --dangerous".format(upgrade_to)
        else:
            cmd = "sudo snap refresh microk8s --channel={}".format(upgrade_to)
        run_until_success(cmd, timeout_insec=600)
        # Allow for the refresh to be processed
        time.sleep(20)
        wait_for_installation(timeout_insec=1200)
