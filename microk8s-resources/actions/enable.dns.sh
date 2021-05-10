#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh
KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
# Apply the dns yaml
# We do not need to see dns pods running at this point just give some slack
echo "Enabling DNS"

read -ra ARGUMENTS <<< "$1"
if [[ ! -z "${ARGUMENTS[@]}" ]]
then
  nameservers="${ARGUMENTS[@]}"
else
  nameservers="8.8.8.8,8.8.4.4"
fi

# if none passed use resolv.conf
if [[ $nameservers == "/etc/resolv.conf" ]]
then
   nameserver_str="/etc/resolv.conf"
else
  REGEX_IP_ADDR='^[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$'
  # get ip addresses separated by , as a list
  nameservers_list=(${nameservers//,/ })
  nameserver_str=""
  for nameserver in "${nameservers_list[@]}"
  do
    if [[ $nameserver =~ $REGEX_IP_ADDR ]]
    then
      nameserver_str="${nameserver_str}${nameserver} "
    else
      echo "Your input value ($nameserver) is not a valid IP address"
      exit 1
    fi
  done
fi

echo "Applying manifest"
ALLOWESCALATION="false"
if grep  -e ubuntu /proc/version | grep 16.04 &> /dev/null
then
  ALLOWESCALATION="true"
fi
declare -A map
map[\$ALLOWESCALATION]="$ALLOWESCALATION"
map[\$NAMESERVERS]="$nameserver_str"
use_manifest coredns apply "$(declare -p map)"
sleep 5

echo "Restarting kubelet"
#TODO(kjackal): do not hardcode the info below. Get it from the yaml
refresh_opt_in_config "cluster-domain" "cluster.local" kubelet
refresh_opt_in_config "cluster-dns" "10.152.183.10" kubelet

restart_service kubelet

echo "DNS is enabled"
