#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Linkerd"
${SNAP}/microk8s-status.wrapper --wait-ready --timeout 30 >/dev/null

echo "Removing linkerd control plane"
KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
"$SNAP_DATA/bin/linkerd" "--kubeconfig=${SNAP_DATA}/credentials/client.config" install "--ignore-cluster" | $KUBECTL delete -f -
"$SNAP_DATA/bin/linkerd" "--kubeconfig=${SNAP_DATA}/credentials/client.config" viz uninstall | $KUBECTL delete -f -
echo "Deleting linkerd binary."
rm -f "$SNAP_DATA/bin/linkerd"


