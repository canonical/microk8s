#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling default storage class"
sudo mkdir -p ${SNAP_COMMON}/default-storage
ARCH=$(arch)
cat "${SNAP}/actions/storage.yaml" | \
"$SNAP/bin/sed" 's@\$SNAP_COMMON@'"$SNAP_COMMON"'@g' | \
"$SNAP/bin/sed" 's@\$ARCH@'"$ARCH"'@g' | \
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply -f -
echo "Storage will be available soon"
