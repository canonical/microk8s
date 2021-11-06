#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

NAMESPACE_PTR="portainer"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

KUBECTL_DELETE_ARGS="--wait=true --timeout=180s --ignore-not-found=true"

echo "Disabling Portainer"

# unload the the manifests
$KUBECTL delete $KUBECTL_DELETE_ARGS -n $NAMESPACE_PTR deployment,service,pods --all  > /dev/null 2>&1


echo "Portainer deployment is disabled"
