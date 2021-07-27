#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Ingress for Kubernetes Dashboard"
"$SNAP/microk8s-enable.wrapper" dashboard
"$SNAP/microk8s-enable.wrapper" ingress
echo "Applying manifest"
use_manifest dashboard-ingress apply

echo "Ingress for Kubernetes Dashboard is enabled"
echo ""
echo "Dashboard will be available at https://kubernetes-dashboard.127.0.0.1.nip.io"