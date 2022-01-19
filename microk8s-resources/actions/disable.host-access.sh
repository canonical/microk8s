#!/usr/bin/env bash

set -e
source $SNAP/actions/common/utils.sh

if [ -f "${SNAP_DATA}/var/lock/host-access-enabled" ]
then
  IP_ADDRESS=$(<"${SNAP_DATA}/var/lock/host-access-enabled")
  echo "Disabling  host-access [${IP_ADDRESS}]"
  "$SNAP/sbin/ip" addr del "$IP_ADDRESS"/32 dev lo label lo:microk8s
  "$SNAP/bin/rm" -f "$SNAP_DATA/var/lock/host-access-enabled"
  echo "Host-access is disabled"
else
  echo "Host-access is not enabled. Nothing to do.."
fi
