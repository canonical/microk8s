#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Linkerd"
refresh_opt_in_config "requestheader-allowed-names" "front-proxy-client" kube-apiserver
sudo systemctl restart snap.${SNAP_NAME}.daemon-apiserver
sleep 5
${SNAP}/microk8s-status.wrapper --wait-ready --timeout 30 >/dev/null

echo "Removing linkerd control plane"
KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
"$SNAP_DATA/bin/linkerd" "--kubeconfig=${SNAP_DATA}/credentials/client.config" install "--ignore-cluster" | $KUBECTL delete -f -
echo "Deleting linkerd binary."
sudo rm -f "$SNAP_DATA/bin/linkerd"


