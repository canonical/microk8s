#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

NAMESPACE_PTR="traefik"
KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
KUBECTL_DELETE_ARGS="--wait=true --timeout=180s --ignore-not-found=true"

echo "Disabling traefik ingress controller"

# unload the the manifests
$KUBECTL delete $KUBECTL_DELETE_ARGS -n $NAMESPACE_PTR -f  "${SNAP}/actions/traefik.yaml"  > /dev/null 2>&1
# delete the "traefik" namespace
$KUBECTL delete $KUBECTL_DELETE_ARGS namespace "$NAMESPACE_PTR" > /dev/null 2>&1 || true

echo "traefik is disabled"
