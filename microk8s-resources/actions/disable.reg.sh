#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Reg"
echo "Removing Reg"
echo "Deleting Reg binary."
sudo rm -f "$SNAP_DATA/bin/reg"
