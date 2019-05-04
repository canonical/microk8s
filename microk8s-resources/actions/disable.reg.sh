#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Reg"
echo "Removing Reg"
#This statement will not terminate the script if there is an error.  Error happens when there is no result returned by getting the resources with label -l "linkerd.io/control-plane-ns"
echo "Deleting Reg binary."
sudo rm -f "$SNAP_DATA/bin/reg"
