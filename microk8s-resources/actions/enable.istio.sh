#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Istio"

# pod/servicegraph will start failing without dns
"$SNAP/microk8s-enable.wrapper" dns

read -p "Enforce mutual TLS authentication (https://bit.ly/2KB4j04) between sidecars? If unsure, choose N. (y/N): " confirm

"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply -f "${SNAP}/actions/istio/crds.yaml"
if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]
then
  "$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply -f "${SNAP}/actions/istio/istio-demo-auth.yaml"
  sudo touch "$SNAP_USER_COMMON/istio-auth.lock"
else
  "$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply -f "${SNAP}/actions/istio/istio-demo.yaml"
  sudo touch "$SNAP_USER_COMMON/istio.lock"
fi

refresh_opt_in_config "allow-privileged" "true" kubelet
refresh_opt_in_config "allow-privileged" "true" kube-apiserver
sudo systemctl restart snap.${SNAP_NAME}.daemon-apiserver
sudo systemctl restart snap.${SNAP_NAME}.daemon-kubelet


echo "Istio is starting"
