#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Metrics-Server"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
# Clean up old metrics-server  
$KUBECTL delete configmap -n kube-system metrics-server-config || true
$KUBECTL delete deployment -n kube-system metrics-server-v0.2.1 || true 

use_manifest metrics-server delete 

echo "Metrics-Server is disabled"
