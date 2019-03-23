#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Linkerd"

echo "Removing linkerd control plane"

"$SNAP_DATA/linkerd" install | "$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" delete -f -

echo "Linkerd is terminating"
echo "Please remove all services injected with Linkerd data plane."
echo "Example: kubectl -n kube-system get deployments.apps -o yaml | microk8s.linkerd uninject - | kubectl apply -f - "
