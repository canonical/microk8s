#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

# check if reg cli is already in the system.  Download if it doesn't exist.
if [ ! -f "${SNAP_DATA}/bin/reg" ]; then
  REG_VERSION="${REG_VERSION:-v0.16.0}"
  echo "Fetching reg version $REG_VERSION."
  sudo mkdir -p "$SNAP_DATA/bin"
  sudo "${SNAP}/usr/bin/curl" -L https://github.com/genuinetools/reg/releases/download/${REG_VERSION}/reg-linux-${SNAP_ARCH} -o "$SNAP_DATA/bin/reg"
  sudo chmod uo+x "$SNAP_DATA/bin/reg"
fi

echo "REG is installed"
