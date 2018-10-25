#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling metrics server"
ARCH=$(arch)
cat "${SNAP}/actions/metrics-server.yaml" | \
"$SNAP/bin/sed" 's@\$ARCH@'"$ARCH"'@g' | \
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" delete -f -
echo "Metrics server is disabled"
