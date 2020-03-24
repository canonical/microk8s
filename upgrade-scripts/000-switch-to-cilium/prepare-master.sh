#!/bin/bash

echo "Preparing master for cilium"

#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

ARCH=$(arch)
if ! [ "${ARCH}" = "amd64" ]; then
  echo "Cilium is not available for ${ARCH}" >&2
  exit 1
fi
