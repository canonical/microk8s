#!/usr/bin/env bash

set -ex

source $SNAP/actions/common/utils.sh

echo "Disabling Knative"

# || true is there to handle race conditions in deleteing resources
KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
$KUBECTL delete -f "$SNAP/actions/knative/" || true

echo "Knative is terminating"
