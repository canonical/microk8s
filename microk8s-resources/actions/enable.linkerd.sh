#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Linkerd"

# pod/servicegraph will start failing without dns
"$SNAP/microk8s-enable.wrapper" dns

"$SNAP/linkerd" install | "$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply -f -

echo "Linkerd is starting"
