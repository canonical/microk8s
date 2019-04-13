#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Linkerd"
echo "Removing linkerd data plane."
"$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" get --all-namespaces daemonset,deploy,job,statefulset -l "linkerd.io/control-plane-ns" -o yaml | "$SNAP_DATA/bin/linkerd" uninject - | "$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" apply -f - 
echo "Removing linkerd control plane"
"$SNAP_DATA/bin/linkerd" install | "$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" delete -f -
echo "Deleting linkerd binary."
sudo rm -f "$SNAP_DATA/bin/linkerd"