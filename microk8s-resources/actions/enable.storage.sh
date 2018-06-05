#!/usr/bin/env bash

set -e

echo "Enabling default storage class"
sudo mkdir -p ${SNAP_COMMON}/default-storage
cat "${SNAP}/actions/storage.yaml" | \
"$SNAP/bin/sed" 's@\$SNAP_COMMON@'"$SNAP_COMMON"'@g' | \
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply -f -
echo "Storage will be available soon"
