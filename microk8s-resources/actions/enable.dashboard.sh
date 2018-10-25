#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling dashboard"
echo "Applying manifest"
ARCH=$(arch)
cat "${SNAP}/actions/dashboard.yaml" | \
"$SNAP/bin/sed" 's@\$ARCH@'"$ARCH"'@g' | \
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply -f -
echo "Dashboard is enabled"
