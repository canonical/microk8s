#!/usr/bin/env bash

set -ex

source $SNAP/actions/common/utils.sh

echo "Enabling Ingress"

ARCH=$(arch)
TAG="0.25.1"
EXTRA_ARGS="- --publish-status-address=127.0.0.1"


declare -A map
map[\$TAG]="$TAG"
map[\$EXTRA_ARGS]="$EXTRA_ARGS"
use_manifest ingress apply "$(declare -p map)"

echo "Ingress is enabled"
