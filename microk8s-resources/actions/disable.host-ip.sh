#!/usr/bin/env bash

set -e
source $SNAP/actions/common/utils.sh

echo "Disabling host-ip"

if [ -f "${SNAP_DATA}/var/lock/host-ip-enabled" ]
then
  IP_ADDRESS=$(<"${SNAP_DATA}/var/lock/host-ip-enabled")
  run_with_sudo "$SNAP/sbin/ifconfig" lo:17 $IP_ADDRESS down
  run_with_sudo "$SNAP/bin/rm" -f "$SNAP_DATA/var/lock/host-ip-enabled"
fi