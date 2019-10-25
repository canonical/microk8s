#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling MetalLB"
read -p "Enter the IP address range (e.g., 10.64.140.43-10.64.140.49): " ip_range
REGEX_IP_RANGE='^(([(\d+)(x+)]){1,3})(\-+([(\d+)(x)]{1,3}))?\.(([(\d+)(x+)]){1,3})(\-+([(\d+)(x)]{1,3}))?\.(([(\d+)(x+)]){1,3})(\-+([(\d+)(x)]{1,3}))?\.(([(\d+)(x+)]){1,3})(\-+([(\d+)(x)]{1,3}))?$'
if [ -z "$var" ]
then
	echo "You have to input IP Range value"
        exit 1
else
        if [[ $ip_range =~ $REGEX_IP_RANGE ]]
	then
		KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
		echo "Applying registry manifest"
		cat ./metallb.yaml | sed "s/{{ip_range}}/$ip_range/g" | $KUBECTL apply -f -
		echo "MetalLB is enabled"
	else
		echo "You input value is not a valid IP Range"
		exit 1
	fi
fi
