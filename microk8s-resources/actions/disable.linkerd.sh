#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Linkerd"
echo "Removing linkerd data plane."
#This statement will not terminate the script if there is an error.  Error happens when there is no result returned by getting the resources with label -l "linkerd.io/control-plane-ns"
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" get --all-namespaces daemonset,deploy,job,statefulset -l "linkerd.io/control-plane-ns" -o yaml  | "$SNAP_DATA/bin/linkerd" uninject - | "$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply -f -  || true
echo "Removing linkerd control plane"
"$SNAP_DATA/bin/linkerd" "--kubeconfig=$SNAP/client.config" install "--ignore-cluster" | "$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" delete -f -
echo "Deleting linkerd binary."
sudo rm -f "$SNAP_DATA/bin/linkerd"