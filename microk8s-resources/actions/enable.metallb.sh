#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling MetalLB"

read -ra ARGUMENTS <<< "$1"
if [ -z "${ARGUMENTS[@]}" ]
then
  read -p "Enter the IP address range (e.g., 10.64.140.43-10.64.140.49): " ip_range
  if [ -z "$var" ]
  then
    echo "You have to input an IP Range value when asked, or provide it as an argument to the enable commang, eg:"
    echo "  microk8s.enable metallb:10.64.140.43-10.64.140.49"
    exit 1
  fi
else
  ip_range=ARGUMENTS[0]
fi

REGEX_IP_RANGE='^(([(\d+)(x+)]){1,3})(\-+([(\d+)(x)]{1,3}))?\.(([(\d+)(x+)]){1,3})(\-+([(\d+)(x)]{1,3}))?\.(([(\d+)(x+)]){1,3})(\-+([(\d+)(x)]{1,3}))?\.(([(\d+)(x+)]){1,3})(\-+([(\d+)(x)]{1,3}))?$'
if [[ $ip_range =~ $REGEX_IP_RANGE ]]
then
  KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
  echo "Applying registry manifest"
  cat $SNAP/actions/metallb.yaml | $SNAP/bin/sed "s/{{ip_range}}/$ip_range/g" | $KUBECTL apply -f -
  echo "MetalLB is enabled"
else
  echo "You input value ($ip_range) is not a valid IP Range"
  exit 1
fi
