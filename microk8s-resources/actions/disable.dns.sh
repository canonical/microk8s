#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling DNS"
echo "Reconfiguring kubelet"

skip_opt_in_config "cluster-domain" kubelet
skip_opt_in_config "cluster-dns" kubelet
sudo systemctl restart snap.${SNAP_NAME}.daemon-kubelet
sleep 5

# Apply the dns yaml
# We do not need to see dns pods running at this point just give some slack
echo "Removing DNS manifest"
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" "delete" "-f" "${SNAP}/actions/dns.yaml"

echo "DNS is disabled"
