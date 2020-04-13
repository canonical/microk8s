#!/usr/bin/env bash

set -e

echo "Disabling host-ip"

if [ -f "${SNAP_DATA}/var/lock/host-ip-enabled" ]
then
  IP_ADDRESS=$(<"${SNAP_DATA}/var/lock/host-ip-enabled")
  sudo ifconfig lo:17 $IP_ADDRESS down
  sudo rm -f "$SNAP_DATA/var/lock/host-ip-enabled"
fi