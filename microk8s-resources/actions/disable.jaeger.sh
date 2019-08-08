#!/usr/bin/env bash

set -e
source $SNAP/actions/common/utils.sh
echo "Disabling Jaeger"
KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
$KUBECTL delete -f "${SNAP}/actions/jaeger"
$KUBECTL delete -f "${SNAP}/actions/jaeger/crds"
echo "The Jaeger operator is disabled"