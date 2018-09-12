#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling NVIDIA GPU support"
use_manifest gpu delete


sudo sh -c "sed 's@\${SNAP}@'"${SNAP}"'@g;s@\${SNAP_DATA}@'"${SNAP_DATA}"'@g;s@\${RUNTIME}@runc@g' $SNAP_DATA/args/containerd-template.toml > $SNAP_DATA/args/containerd.toml"

sudo systemctl restart snap.${SNAP_NAME}.daemon-containerd
containerd_up=$(wait_for_service containerd)
if [[ $containerd_up == fail ]]
then
  echo "Containerd did not start on time. Proceeding."
fi
# Allow for some seconds for containerd processes to start
sleep 10

echo "GPU support disabled"
