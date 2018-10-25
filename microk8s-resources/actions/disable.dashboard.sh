#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling dashboard"
ARCH=$(arch)
cat "${SNAP}/actions/dashboard.yaml" | \
"$SNAP/bin/sed" 's@\$ARCH@'"$ARCH"'@g' | \
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" delete -f -
echo "Dashboard is disabled"
