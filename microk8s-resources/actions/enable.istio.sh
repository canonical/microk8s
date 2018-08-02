#!/usr/bin/env bash

set -e

refresh_opt_in_config() {
    opt="--$1"
    value="$2"
    config_file="$SNAP_DATA/args/$3"
    replace_line="$opt=$value"
    if $(grep -qE "^$opt=" $config_file); then
        sudo "$SNAP/bin/sed" -i "s/^$opt=.*/$replace_line/" $config_file
    else
        sudo "$SNAP/bin/sed" -i "$ a $replace_line" "$config_file"
    fi
}

echo "Enabling Istio"

# pod/servicegraph will start failing without dns
"$SNAP/microk8s-enable.wrapper" dns

read -p "Enforce mutual TLS authentication between sidecars? (Y/N): " confirm

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


echo "Istio is coming up"
