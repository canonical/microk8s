#!/bin/bash

set -e

echo "Praparing node for cilium"
source $SNAP/actions/common/utils.sh

ARCH=$(arch)
if ! [ "${ARCH}" = "amd64" ]; then
  echo "Cilium is not available for ${ARCH}" >&2
  exit 1
fi

if ! [ -e "$SNAP"/microk8s-resources/cni/cilium/05-cilium-cni.conf ]; then
  echo "Cilium is not available on this snap revision" >&2
  exit 2
fi
