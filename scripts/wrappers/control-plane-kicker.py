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

services = [
    'controller-manager',
    'scheduler',
]


def start_control_plane_services():
    for service in services:
        if not is_service_expected_to_start(service):
            systemd_service_name = "microk8s.daemon-{}".format(service)
            print("Starting {}".format(systemd_service_name), flush=True)
            cmd = "snapctl start {}".format(systemd_service_name)
            subprocess.check_output((cmd.split()))
            set_service_expected_to_start(service, True)


def stop_control_plane_services():
    for service in services:
        if is_service_expected_to_start(service):
            systemd_service_name = "microk8s.daemon-{}".format(service)
            print("Stopping {}".format(systemd_service_name), flush=True)
            cmd = "snapctl stop {}".format(systemd_service_name)
            subprocess.check_output(cmd.split())
            set_service_expected_to_start(service, False)


if __name__ == '__main__':
    while True:
        sleep(10)

        try:
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

            print(voter_ips)
            print(local_ips)

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
