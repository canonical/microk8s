#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

NAMESPACE_PTR="traefik"
KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

echo "Enabling traefik ingress controller on port 8080"

# make sure the "traefik" namespace exists
$KUBECTL create namespace "$NAMESPACE_PTR" > /dev/null 2>&1 || true
# load the CRD and wait for it to be installed
$KUBECTL apply -f "${SNAP}/actions/traefik.yaml"

echo "traefik ingress controller has been installed on port 8080"
