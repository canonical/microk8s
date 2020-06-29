#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

if $KUBECTL get ns metallb-system >/dev/null 2>&1
then
  echo "MetalLB already enabled."
  exit 0
fi

echo "Enabling MetalLB"

ALLOWESCALATION=false
if grep  -e ubuntu /proc/version | grep 16.04 &> /dev/null
then
  ALLOWESCALATION=true
fi

read -ra ARGUMENTS <<< "$1"
if [ -z "${ARGUMENTS[@]}" ]
then
  read -p "Enter each IP address range delimited by comma (e.g. '10.64.140.43-10.64.140.49,192.168.0.105-192.168.0.111'): " ip_range_input
  if [ -z "${ip_range_input}" ]
  then
    echo "You have to input an IP Range value when asked, or provide it as an argument to the enable command, eg:"
    echo "  microk8s enable metallb:10.64.140.43-10.64.140.49,192.168.0.105-192.168.0.111"
    exit 1
  fi
else
  ip_range_input="${ARGUMENTS[@]}"
fi

REGEX_IP_RANGE='^[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*-[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$'
ip_ranges=(`echo $ip_range_input | sed 's/,/\n/g'`)
ip_range_str="addresses:"
for ip_range in "${ip_ranges[@]}"
do
  if [[ $ip_range =~ $REGEX_IP_RANGE ]]
  then
    ip_range_str="${ip_range_str}\n      - ${ip_range}"
  else
    echo "Your input value ($ip_range) is not a valid IP Range"
    exit 1
  fi
  echo "Applying registry manifest"
  cat $SNAP/actions/metallb.yaml | $SNAP/bin/sed "s/{{allow_escalation}}/$ALLOWESCALATION/g" | $SNAP/bin/sed "s/{{addresses}}/$ip_range_str/g" | $KUBECTL apply -f -
done
