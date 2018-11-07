#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling default storage"
declare -A map
map[\$SNAP_COMMON]="$SNAP_COMMON"
use_manifest storage delete "$(declare -p map)"
sleep 5
echo "Storage removed"
read -p "Remove PVC storage at $SNAP_COMMON/default-storage ? (Y/N): " confirm && [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]] || exit 1
sudo rm -rf "$SNAP_COMMON/default-storage"
echo "Storage space reclaimed"
