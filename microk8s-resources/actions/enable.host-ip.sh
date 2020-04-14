#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

read -ra IP_ADDRESS <<< "$1"

if [ -z "$IP_ADDRESS" ]
then
  IP_ADDRESS="10.0.7.17"
else
  IP_ADDRESS="$1"
  if ! valid_ip "${IP_ADDRESS[*]}";
  then
    echo "Bad IP[${IP_ADDRESS}]. Please provide a valid IP address. Default is 10.0.7.17";
    exit
  fi
fi
echo "$IP_ADDRESS" > "${SNAP_DATA}/var/lock/host-ip-enabled"
echo "Setting ${IP_ADDRESS} as host-ip"

run_with_sudo "$SNAP/sbin/ifconfig" lo:17 "$IP_ADDRESS" up


