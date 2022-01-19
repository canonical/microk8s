#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

if [ -d "$SNAP_COMMON/default-storage" ]
then
  echo "Hostpath storage is already enabled."
  exit 0
fi

echo "Enabling default storage class."
echo "WARNING: Hostpath storage is not suitable for production environments."
echo ""
mkdir -p ${SNAP_COMMON}/default-storage

declare -A map
map[\$SNAP_COMMON]="$SNAP_COMMON"
use_manifest storage apply "$(declare -p map)"
echo "Storage will be available soon."

if [ -e ${SNAP_DATA}/var/lock/clustered.lock ]
then
  echo ""
  echo "WARNING: The storage class enabled does not persist volumes across nodes."
  echo ""
fi
