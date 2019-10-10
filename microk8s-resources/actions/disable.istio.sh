#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Istio"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

$KUBECTL delete namespaces istio-system
rm -rf "${SNAP_DATA}/bin/istioctl"
rm -rf "$SNAP_USER_COMMON/istio-auth.lock"
rm -rf "$SNAP_USER_COMMON/istio.lock"

echo "Istio is terminating"
