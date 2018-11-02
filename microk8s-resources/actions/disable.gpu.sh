#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling NVIDIA GPU support"
skip_opt_in_config "default-runtime" dockerd
sudo systemctl restart snap.${SNAP_NAME}.daemon-kubelet
use_manifest gpu delete
echo "GPU support disabled"
