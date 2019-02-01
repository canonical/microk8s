#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Prometheus"
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" delete -f "${SNAP}/actions/prometheus"
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" delete -f "${SNAP}/actions/prometheus/resources"

echo "The Prometheus operator is disabled"
