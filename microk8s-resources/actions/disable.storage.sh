#!/usr/bin/env bash

set -e

echo "Disabling default storage"
cat "${SNAP}/actions/storage.yaml" | \
"$SNAP/bin/sed" 's@\$SNAP_COMMON@'"$SNAP_COMMON"'@g' | \
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" delete -f -
sleep 5
echo "Storage removed"
read -p "Remove PVC storage at $SNAP_COMMON/default-storage ? (Y/N): " confirm && [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]] || exit 1
sudo rm -rf "$SNAP_COMMON/default-storage"
echo "Storage space reclaimed"
