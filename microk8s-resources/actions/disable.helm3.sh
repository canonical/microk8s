#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Helm 3"

if [ -f "${SNAP_DATA}/bin/helm3" ]
then
  sudo rm -f "$SNAP_DATA/bin/helm3"
fi
