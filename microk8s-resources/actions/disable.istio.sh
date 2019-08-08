#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Istio"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

$KUBECTL delete namespaces istio-system
$KUBECTL delete -f "${SNAP}/actions/istio/crds.yaml" -n istio-system &> /dev/null || true

echo "Istio is terminating"
