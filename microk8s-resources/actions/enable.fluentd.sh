#!/usr/bin/env bash

set -e

export PATH="$SNAP/usr/sbin:$SNAP/usr/bin:$SNAP/sbin:$SNAP/bin:$PATH"

source $SNAP/actions/common/utils.sh

echo "Enabling Fluentd-Elasticsearch"

echo "Labeling nodes"
NODENAME="$("$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" get no -o yaml | grep " name:"| awk '{print $2}')"
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" label nodes "$NODENAME" beta.kubernetes.io/fluentd-ds-ready=true || true


"$SNAP/microk8s-enable.wrapper" dns
sleep 5

refresh_opt_in_config "allow-privileged" "true" kubelet
refresh_opt_in_config "allow-privileged" "true" kube-apiserver
sudo systemctl restart snap.${SNAP_NAME}.daemon-apiserver
sudo systemctl restart snap.${SNAP_NAME}.daemon-kubelet

sleep 5

"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply -f "${SNAP}/actions/fluentd"

echo "Fluentd-Elasticsearch is enabled"