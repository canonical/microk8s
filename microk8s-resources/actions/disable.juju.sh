#!/usr/bin/env bash

set -eu

source $SNAP/actions/common/utils.sh

function disable_juju() {
  echo "Removing Juju..."
  if [ -f "${SNAP_DATA}/bin/juju" ]; then
    run_with_sudo rm -rf "$SNAP_DATA/bin/juju"
    run_with_sudo rm -rf "$SNAP_DATA/juju"
    echo "Juju is now disabled."
  else
    echo "Juju has already been disabled."
  fi
}

disable_juju
