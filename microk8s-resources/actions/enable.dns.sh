#!/usr/bin/env bash

set -ex

source $SNAP/actions/common/utils.sh

# Apply the dns yaml
# We do not need to see dns pods running at this point just give some slack
echo "Enabling DNS"
echo "Applying manifest"
ALLOWESCALATION="false"
if grep  -e ubuntu /proc/version | grep 16.04 &> /dev/null
then
  ALLOWESCALATION="true"
fi
declare -A map
map[\$ALLOWESCALATION]="$ALLOWESCALATION"
use_manifest coredns apply "$(declare -p map)"
sleep 5

echo "Restarting kubelet"
#TODO(kjackal): do not hardcode the info below. Get it from the yaml
refresh_opt_in_config "cluster-domain" "cluster.local" kubelet
refresh_opt_in_config "cluster-dns" "10.152.183.10" kubelet

restart_service kubelet

echo "DNS is enabled"
