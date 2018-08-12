#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Istio"

"$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" delete namespaces istio-system
"$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" delete -f "${SNAP}/actions/istio/crds.yaml" -n istio-system &> /dev/null || true

echo "Istio is terminating"
