#!/usr/bin/python3
import netifaces
import subprocess

from time import sleep

from common.utils import (
    is_cluster_ready,
    get_dqlite_info,
    is_ha_enabled,
    is_service_expected_to_start,
    set_service_expected_to_start,
)
import os

services = [
    'controller-manager',
    'scheduler',
]


def start_control_plane_services():
    """
    Start the control plane services
    """
    for service in services:
        if not is_service_expected_to_start(service):
            systemd_service_name = "microk8s.daemon-{}".format(service)
            print("Starting {}".format(systemd_service_name), flush=True)
            cmd = "snapctl start {}".format(systemd_service_name)
            subprocess.check_output((cmd.split()))
            set_service_expected_to_start(service, True)


def stop_control_plane_services():
    """
    Stop the control plane services
    """
    for service in services:
        if is_service_expected_to_start(service):
            systemd_service_name = "microk8s.daemon-{}".format(service)
            print("Stopping {}".format(systemd_service_name), flush=True)
            cmd = "snapctl stop {}".format(systemd_service_name)
            subprocess.check_output(cmd.split())
            set_service_expected_to_start(service, False)


def microk8s_group_exists():
    """
    Check the existence of the microk8s group
    :return: True is the microk8s group exists
    """
    try:
        cmd = "getent group microk8s"
        subprocess.check_call(cmd.split())
        return True
    except:
        return False


def set_dqlite_file_permissions():
    """
    Set the file permissions in the dqlite backend directory
    """
    dqlite_path = os.path.expandvars("${SNAP_DATA}/var/kubernetes/backend")
    try:
        cmd = "chmod -R ug+rwX {}".format(dqlite_path)
        subprocess.check_call(cmd.split())
        cmd = "chgrp microk8s -R {}".format(dqlite_path)
        subprocess.check_call(cmd.split())
    except Exception as e:
        print("Failed to set the file permissions in dqlite.")
        print(e)


if __name__ == '__main__':
    while True:
        # Check for changes every 10 seconds
        sleep(10)
        try:

            if microk8s_group_exists():
                set_dqlite_file_permissions()

            # We will not attempt to stop services if:
            # 1. The cluster is not ready
            # 2. We are not on an HA cluster
            # 3. The control plane kicker is disabled
            # 4. dqlite has less than 4 nodes
            if (
                not is_cluster_ready()
                or not is_ha_enabled()
                or not is_service_expected_to_start('control-plane-kicker')
            ):
                start_control_plane_services()
                continue

            info = get_dqlite_info()
            if len(info) <= 3:
                start_control_plane_services()
                continue

            local_ips = []
            for interface in netifaces.interfaces():
                if netifaces.AF_INET not in netifaces.ifaddresses(interface):
                    continue
                for link in netifaces.ifaddresses(interface)[netifaces.AF_INET]:
                    local_ips.append(link['addr'])

            voter_ips = []
            for node in info:
                if node[1] == "voter":
                    ip_parts = node[0].split(':')
                    voter_ips.append(ip_parts[0])

            should_run = False
            for ip in local_ips:
                if ip in voter_ips:
                    should_run = True
                    start_control_plane_services()
                    break

            if not should_run:
                stop_control_plane_services()

        except Exception as e:
            print(e, flush=True)
