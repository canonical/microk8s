#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

readonly CONFIG="$SNAP_DATA/args/containerd-template.toml"
readonly SOCKET="$SNAP_COMMON/run/containerd.sock"

echo "Enabling NVIDIA GPU"

read -ra ARGUMENTS <<< "$1"

if [[ "$ARGUMENTS" == "force-system-driver" ]]
  then
  echo "Using host driver"
  readonly ENABLE_INTERNAL_DRIVER="false"
elif [[ "$ARGUMENTS" == "force-operator-driver" ]]
  then
  echo "Using operator driver"
  readonly ENABLE_INTERNAL_DRIVER="true"
else
  if lsmod | grep "nvidia" &> /dev/null
    then
    echo "Using host driver"
    readonly ENABLE_INTERNAL_DRIVER="false"
  else
    echo "Using operator driver"
    readonly ENABLE_INTERNAL_DRIVER="true"
  fi
fi

sudo mkdir -p ${SNAP_DATA}/var/lock
sudo touch ${SNAP_DATA}/var/lock/gpu

"$SNAP/microk8s-enable.wrapper" dns
"$SNAP/microk8s-enable.wrapper" helm3

echo "Installing NVIDIA Operator"

"$SNAP/microk8s-helm3.wrapper" repo add nvidia https://nvidia.github.io/gpu-operator
"$SNAP/microk8s-helm3.wrapper" repo update
"$SNAP/microk8s-helm3.wrapper" install gpu-operator nvidia/gpu-operator \
  --version=v1.8.2 \
  --set toolkit.version=1.5.0-ubuntu18.04 \
  --set operator.defaultRuntime=containerd \
  --set driver.enabled=$ENABLE_INTERNAL_DRIVER \
  --set toolkit.env[0].name=CONTAINERD_CONFIG \
  --set toolkit.env[0].value=$CONFIG \
  --set toolkit.env[1].name=CONTAINERD_SOCKET \
  --set toolkit.env[1].value=$SOCKET

echo "NVIDIA is enabled"
