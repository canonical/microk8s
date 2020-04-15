#!/usr/bin/env bash

set -e
source $SNAP/actions/common/utils.sh

if [ -f "${SNAP_DATA}/var/lock/host-ip-enabled" ]
then
  IP_ADDRESS=$(<"${SNAP_DATA}/var/lock/host-ip-enabled")
  echo "Disabling  host-ip [${IP_ADDRESS}]"
  run_with_sudo "$SNAP/sbin/ifconfig" lo:1 $IP_ADDRESS down
  run_with_sudo "$SNAP/bin/rm" -f "$SNAP_DATA/var/lock/host-ip-enabled"
  echo "Host-ip is disabled"
else
  echo "The host-ip is not enabled. Nothing to do.."
fi

