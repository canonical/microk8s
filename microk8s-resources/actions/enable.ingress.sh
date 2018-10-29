#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Ingress"

ARCH=$(arch)
TAG="0.15.0"
if [ "${ARCH}" = arm64 ]
then
  TAG="0.11.0"
fi
cat "${SNAP}/actions/ingress.yaml" | \
"$SNAP/bin/sed" 's@\$ARCH@'"$ARCH"'@g' | \
"$SNAP/bin/sed" 's@\$TAG@'"$TAG"'@g' | \
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply -f -

echo "Ingress is enabled"
