#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Knative"

"$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" delete namespaces  knative-serving knative-build knative-eventing knative-sources knative-monitoring

echo "Knative is terminating"
