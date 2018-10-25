#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling ingress"
ARCH=$(arch)
cat "${SNAP}/actions/ingress.yaml" | \
"$SNAP/bin/sed" 's@\$ARCH@'"$ARCH"'@g' | \
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" delete -f -
echo "Ingress is disabled"
