#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling default storage"
read -ra ARGUMENTS <<< "$1"

declare -A map
map[\$SNAP_COMMON]="$SNAP_COMMON"
use_manifest storage delete "$(declare -p map)"
sleep 5
echo "Storage removed"
if [ ! -z "${ARGUMENTS[@]}" ] && [ "${ARGUMENTS[@]}" = "destroy-storage" ]
then
  rm -rf "$SNAP_COMMON/default-storage"
  echo "Storage space reclaimed"
else
  read -p "Remove PVC storage at $SNAP_COMMON/default-storage ? (Y/N): " confirm && [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]] || exit 1
  rm -rf "$SNAP_COMMON/default-storage"
  echo "Storage space reclaimed"
fi
