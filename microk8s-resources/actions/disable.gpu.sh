#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling NVIDIA GPU support"

"$SNAP/microk8s-helm3.wrapper" uninstall gpu-operator

echo "GPU support disabled"
