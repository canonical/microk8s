#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Ingress for Kubernetes Dashboard"
use_manifest dashboard-ingress delete
echo "Ingress for Kubernetes Dashboard is disabled"
