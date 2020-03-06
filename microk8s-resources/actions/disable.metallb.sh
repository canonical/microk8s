#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling MetalLB"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

$KUBECTL delete namespaces metallb-system

echo "MetalLB is terminating"
