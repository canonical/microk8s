#!/usr/bin/env bash

set -eu

export PATH="$SNAP/usr/sbin:$SNAP/usr/bin:$SNAP/sbin:$SNAP/bin:$PATH"
ARCH="$($SNAP/bin/uname -m)"
export IN_SNAP_LD_LIBRARY_PATH="$SNAP/lib:$SNAP/usr/lib:$SNAP/lib/$ARCH-linux-gnu:$SNAP/usr/lib/$ARCH-linux-gnu"

source $SNAP/actions/common/utils.sh

exit_if_no_permissions

sudo ${SNAP}/usr/bin/python3 ${SNAP}/actions/common/containerd-config-migrate.py
