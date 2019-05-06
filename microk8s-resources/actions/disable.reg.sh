#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Reg"
sudo rm -f "$SNAP_DATA/bin/reg"
