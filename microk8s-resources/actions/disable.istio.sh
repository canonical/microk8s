#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Istio"

skip_opt_in_config "allow-privileged" kubelet
skip_opt_in_config "allow-privileged" kube-apiserver
sudo systemctl restart snap.${SNAP_NAME}.daemon-apiserver
sudo systemctl restart snap.${SNAP_NAME}.daemon-kubelet
while ! (sudo systemctl is-active --quiet snap.${SNAP_NAME}.daemon-apiserver) ||
      ! (sudo systemctl is-active --quiet snap.${SNAP_NAME}.daemon-kubelet) ||
      ! ("$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" get all --all-namespaces &> /dev/null)
do
  sleep 1
done
sleep 1

"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" delete namespaces istio-system
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" delete -f "${SNAP}/actions/istio/crds.yaml" -n istio-system &> /dev/null || true

echo "Istio is terminating"
