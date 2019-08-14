#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Helm"

if [ -f "${SNAP_DATA}/bin/helm" ]
then
  sudo rm -f "$SNAP_DATA/bin/helm"
fi
