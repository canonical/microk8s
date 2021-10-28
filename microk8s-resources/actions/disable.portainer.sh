#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

NAMESPACE_PTR="portainer"

#MANIFEST_PTR="https://raw.githubusercontent.com/portainer/k8s/master/deploy/manifests/portainer/portainer.yaml"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

KUBECTL_DELETE_ARGS="--wait=true --timeout=180s --ignore-not-found=true"

echo "Disabling Portainer"

# unload the the manifests
#$KUBECTL delete $KUBECTL_DELETE_ARGS -n $NAMESPACE_PTR -f "$MANIFEST_PTR" > /dev/null 2>&1
$KUBECTL delete $KUBECTL_DELETE_ARGS -n $NAMESPACE_PTR deployment,service,pods --all  > /dev/null 2>&1

# delete the "portainer" namespace
#$KUBECTL delete $KUBECTL_DELETE_ARGS namespace "$NAMESPACE_PTR" > /dev/null 2>&1 || true

echo "Portainer is disabled"
