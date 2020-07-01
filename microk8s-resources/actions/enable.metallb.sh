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
  read -p "Enter the IP address range (e.g., 10.64.140.43-10.64.140.49): " ip_range
  if [ -z "${ip_range}" ]
  then
    echo "You have to input an IP Range value when asked, or provide it as an argument to the enable command, eg:"
    echo "  microk8s enable metallb:10.64.140.43-10.64.140.49"
    exit 1
  fi
else
  ip_range="${ARGUMENTS[@]}"
fi

REGEX_IP_RANGE='^[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*-[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$'
if [[ $ip_range =~ $REGEX_IP_RANGE ]]
then
  echo "Applying registry manifest"
  cat $SNAP/actions/metallb.yaml | $SNAP/bin/sed "s/{{allow_escalation}}/$ALLOWESCALATION/g" | $SNAP/bin/sed "s/{{ip_range}}/$ip_range/g" | $KUBECTL apply -f -
  echo "MetalLB is enabled"
else
  echo "You input value ($ip_range) is not a valid IP Range"
  exit 1
fi
