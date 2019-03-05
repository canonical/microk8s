#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Ingress"

ARCH=$(arch)
TAG="0.22.0"
EXTRA_ARGS="- --publish-status-address=127.0.0.1"
if [ "${ARCH}" = arm64 ]
then
  TAG="0.11.0"
  EXTRA_ARGS=""
fi

declare -A map
map[\$TAG]="$TAG"
map[\$EXTRA_ARGS]="$EXTRA_ARGS"
use_manifest ingress apply "$(declare -p map)"

echo "Ingress is enabled"
