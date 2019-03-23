#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

# Apply the dns yaml
# We do not need to see dns pods running at this point just give some slack
echo "Enabling DNS"
echo "Applying manifest"
use_manifest dns apply
sleep 5

echo "Restarting kubelet"
#TODO(kjackal): do not hardcode the info below. Get it from the yaml
refresh_opt_in_config "cluster-domain" "cluster.local" kubelet
refresh_opt_in_config "cluster-dns" "10.152.183.10" kubelet

sudo systemctl restart snap.${SNAP_NAME}.daemon-kubelet

echo "DNS is enabled"
