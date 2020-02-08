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
  run_with_sudo rm -rf "$SNAP_COMMON/default-storage"
  echo "Storage space reclaimed"
else
  echo "Storage space preserved"
fi

