#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "DEPRECIATION WARNING: 'storage' is deprecated and will soon be removed. Please use 'hostpath-storage' instead."
echo ""

"$SNAP/microk8s-enable.wrapper" hostpath-storage
