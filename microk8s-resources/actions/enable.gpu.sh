#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling NVIDIA GPU"
if lsmod | grep "nvidia" &> /dev/null ; then
  echo "NVIDIA kernel module detected"
else
  echo "Aborting: NVIDIA kernel module not loaded."
  echo "Please ensure you have CUDA capable hardware and the NVIDIA drivers installed."
  exit 1
fi

refresh_opt_in_config "default-runtime" "nvidia" dockerd
sudo systemctl restart snap.${SNAP_NAME}.daemon-docker
sleep 10

/snap/bin/microk8s.enable dns

echo "Applying manifest"
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" "apply" "-f" "${SNAP}/actions/gpu.yaml"

echo "NVIDIA is enabled"
