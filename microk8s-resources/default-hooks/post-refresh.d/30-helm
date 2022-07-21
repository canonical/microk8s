#!/bin/bash

# Install helm binaries in SNAP_DATA to maintain backwards-compatibility
if [ -d "${SNAP_DATA}/bin" ]; then
  cp "${SNAP}/bin/helm" "${SNAP_DATA}/bin/helm3"
fi
