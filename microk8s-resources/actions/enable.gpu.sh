#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

readonly CONFIG="$SNAP_DATA/args/containerd-template.toml"
readonly SOCKET="$SNAP_COMMON/run/containerd.sock"

echo "Enabling NVIDIA GPU"

sudo mkdir -p ${SNAP_DATA}/var/lock
sudo touch ${SNAP_DATA}/var/lock/gpu

"$SNAP/microk8s-enable.wrapper" dns
"$SNAP/microk8s-enable.wrapper" helm3

echo "Installing NVIDIA Operator"

"$SNAP/microk8s-helm3.wrapper" repo add nvidia https://nvidia.github.io/gpu-operator
"$SNAP/microk8s-helm3.wrapper" repo update
"$SNAP/microk8s-helm3.wrapper" install gpu-operator nvidia/gpu-operator \
  --set operator.defaultRuntime=containerd \
  --set toolkit.version=1.4.1-ubuntu16.04 \
  --set toolkit.env[0].name=CONTAINERD_CONFIG \
  --set toolkit.env[0].value=$CONFIG \
  --set toolkit.env[1].name=CONTAINERD_SOCKET \
  --set toolkit.env[1].value=$SOCKET

echo "NVIDIA is enabled"
