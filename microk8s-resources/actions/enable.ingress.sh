#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Ingress"

ARCH=$(arch)
TAG="0.15.0"
if [ "${ARCH}" = arm64 ]
then
  TAG="0.11.0"
fi

declare -A map
map[\$TAG]="$TAG"
use_manifest ingress apply "$(declare -p map)"

echo "Ingress is enabled"
