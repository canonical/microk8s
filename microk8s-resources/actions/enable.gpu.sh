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

sudo mkdir -p ${SNAP_DATA}/var/lock
sudo touch ${SNAP_DATA}/var/lock/gpu

sudo systemctl restart snap.${SNAP_NAME}.daemon-containerd
containerd_up=$(wait_for_service containerd)
if [[ $containerd_up == fail ]]
then
  echo "Containerd did not start on time. Proceeding."
fi
# Allow for some seconds for containerd processes to start
sleep 10

"$SNAP/microk8s-enable.wrapper" dns

echo "Applying manifest"
use_manifest gpu apply
echo "NVIDIA is enabled"
