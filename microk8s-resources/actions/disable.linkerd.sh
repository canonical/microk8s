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
<<<<<<< d2713cf4c8e0e2e01c4e7b1cecf835993f4d86d6
sudo rm -f "$SNAP_DATA/bin/linkerd"
=======
rm -f "$SNAP_DATA/bin/linkerd"

# temporary fix while we wait for linkerd to support v1.16
skip_opt_in_config "runtime-config" kube-apiserver
echo "Restarting the API server."
snapctl restart ${SNAP_NAME}.daemon-apiserver
sleep 5
${SNAP}/microk8s-status.wrapper --wait-ready --timeout 30 >/dev/null

>>>>>>> Remove sudo
