#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

OF_NAMESPACE="openfaas"
FN_NAMESPACE="openfaas-fn"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

KUBECTL_DELETE_ARGS="--wait=true --timeout=180s --ignore-not-found=true"

echo "Disabling OpenFaaS"

# unload the the  crd


# delete the namespaces
$KUBECTL delete $KUBECTL_DELETE_ARGS namespace "$OF_NAMESPACE" > /dev/null 2>&1 || true
$KUBECTL delete $KUBECTL_DELETE_ARGS namespace "$FN_NAMESPACE" > /dev/null 2>&1 || true
$KUBECTL delete $KUBECTL_DELETE_ARGS crd \
    functioningresses.openfaas.com \
    profiles.openfaas.com \
    functions.openfaas.com 

echo "OpenFaaS is disabled"
