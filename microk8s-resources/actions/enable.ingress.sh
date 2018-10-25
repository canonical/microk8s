#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling ingress"
echo "Applying manifest"
ARCH=$(arch)
cat "${SNAP}/actions/ingress.yaml" | \
"$SNAP/bin/sed" 's@\$ARCH@'"$ARCH"'@g' | \
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply -f -
echo "Ingress is enabled"
