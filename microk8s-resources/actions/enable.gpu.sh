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
TRY_ATTEMPT=0
while (! (sudo systemctl is-active --quiet snap.${SNAP_NAME}.daemon-docker) ||
      ! (sudo "$SNAP/usr/bin/docker" "-H" "unix://${SNAP_DATA}/docker.sock" ps &> /dev/null)) &&
      ! [ ${TRY_ATTEMPT} -eq 30 ]
do
  TRY_ATTEMPT=$((TRY_ATTEMPT+1))
  sleep 1
done
if [ ${TRY_ATTEMPT} -eq 30 ]
then
  echo "Snapped docker not responding after 30 seconds. Proceeding"
fi

"$SNAP/microk8s-enable.wrapper" dns

echo "Applying manifest"
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" "apply" "-f" "${SNAP}/actions/gpu.yaml"

echo "NVIDIA is enabled"
