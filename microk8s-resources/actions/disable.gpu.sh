#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling NVIDIA GPU support"
skip_opt_in_config "default-runtime" dockerd
sudo systemctl restart snap.${SNAP_NAME}.daemon-kubelet
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" "delete" "-f" "${SNAP}/actions/gpu.yaml"
echo "GPU support disabled"
