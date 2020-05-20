#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

if ! [ -e "$SNAP_DATA/var/lock/clustered.lock" ]
then
  echo "Disabling NVIDIA GPU support"
  use_manifest gpu delete
fi

run_with_sudo rm -rf ${SNAP_DATA}/var/lock/gpu

run_with_sudo preserve_env snapctl restart "${SNAP_NAME}.daemon-containerd"
containerd_up=$(wait_for_service containerd)
if [[ $containerd_up == fail ]]
then
  echo "Containerd did not start on time. Proceeding."
fi
# Allow for some seconds for containerd processes to start
sleep 10

echo "GPU support disabled"
