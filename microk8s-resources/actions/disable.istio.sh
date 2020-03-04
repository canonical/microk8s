#!/usr/bin/env bash

set -ex

source $SNAP/actions/common/utils.sh

echo "Disabling Istio"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

$KUBECTL delete namespaces istio-system
run_with_sudo rm -rf "${SNAP_DATA}/bin/istioctl"
run_with_sudo rm -rf "$SNAP_USER_COMMON/istio-auth.lock"
run_with_sudo rm -rf "$SNAP_USER_COMMON/istio.lock"

echo "Istio is terminating"
