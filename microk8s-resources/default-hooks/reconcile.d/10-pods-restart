#!/bin/bash

. "${SNAP}/actions/common/utils.sh"

if ! [ -e "${SNAP_DATA}/var/lock/no-cni-reload" ] &&
  [ -e "${SNAP_DATA}/var/lock/snapdata-mounts-need-reload" ]; then
  if (is_apiserver_ready) && "${SNAP}/scripts/kill-host-pods.py" --with-snap-data-mounts --with-owner -- -A; then
    rm "${SNAP_DATA}/var/lock/snapdata-mounts-need-reload"
  fi
fi
