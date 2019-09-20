#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Linkerd"
echo "Removing linkerd control plane"
KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
"$SNAP_DATA/bin/linkerd" "--kubeconfig=${SNAP_DATA}/credentials/client.config" install "--ignore-cluster" | $KUBECTL delete -f -
echo "Deleting linkerd binary."
sudo rm -f "$SNAP_DATA/bin/linkerd"

# temporary fix while we wait for linkerd to support v1.16
skip_opt_in_config "runtime-config" kube-apiserver
echo "Restarting the API server."
sudo systemctl restart snap.${SNAP_NAME}.daemon-apiserver
sleep 5
${SNAP}/microk8s-status.wrapper --wait-ready --timeout 30 >/dev/null

