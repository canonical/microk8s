#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling metrics server"
echo "Applying manifest"
ARCH=$(arch)
cat "${SNAP}/actions/metrics-server.yaml" | \
"$SNAP/bin/sed" 's@\$ARCH@'"$ARCH"'@g' | \
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply -f -
echo "Metrics server is enabled"
