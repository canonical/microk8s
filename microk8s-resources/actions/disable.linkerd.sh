#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Linkerd"
echo "Removing linkerd data plane."
#This statement will not terminate the script if there is an error.  Error happens when there is no result returned by getting the resources with label -l "linkerd.io/control-plane-ns"
KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
$KUBECTL get --all-namespaces daemonset,deploy,job,statefulset -l "linkerd.io/control-plane-ns" -o yaml  | "$SNAP_DATA/bin/linkerd" uninject - | $KUBECTL apply -f -  || true
echo "Removing linkerd control plane"
"$SNAP_DATA/bin/linkerd" "--kubeconfig=${SNAP_DATA}/credentials/client.config" install "--ignore-cluster" | $KUBECTL delete -f -
echo "Deleting linkerd binary."
sudo rm -f "$SNAP_DATA/bin/linkerd"
