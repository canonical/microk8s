#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Knative"

# || true is there to handle race conditions in deleteing resources
"$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" delete -f "$SNAP/actions/knative/" || true

echo "Knative is terminating"
