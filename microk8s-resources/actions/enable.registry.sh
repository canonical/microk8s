#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling the private registry"

"$SNAP/microk8s-enable.wrapper" storage

echo "Applying registry manifest"
use_manifest registry apply

echo "The registry is enabled"
