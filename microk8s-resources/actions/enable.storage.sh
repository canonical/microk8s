#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling default storage class"
sudo mkdir -p ${SNAP_COMMON}/default-storage

declare -A map
map[\$SNAP_COMMON]="$SNAP_COMMON"
use_manifest storage apply "$(declare -p map)"
echo "Storage will be available soon"
