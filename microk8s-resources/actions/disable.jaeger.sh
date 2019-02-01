#!/usr/bin/env bash

set -e
source $SNAP/actions/common/utils.sh
echo "Disabling Jaeger"
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" delete -f "${SNAP}/actions/jaeger"
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" delete -f "${SNAP}/actions/jaeger/crds"
echo "The Jaeger operator is disabled"