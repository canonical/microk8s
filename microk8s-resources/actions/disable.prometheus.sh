#!/usr/bin/env bash

set -ex

source $SNAP/actions/common/utils.sh

echo "Disabling Prometheus"
KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

$KUBECTL delete -f "${SNAP}/actions/prometheus"
$KUBECTL delete -f "${SNAP}/actions/prometheus/setup"

echo "The Prometheus operator is disabled"
