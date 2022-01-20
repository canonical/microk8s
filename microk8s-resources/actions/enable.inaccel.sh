#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

"$SNAP/microk8s-enable.wrapper" dns helm3

echo "Enabling InAccel FPGA Operator"

"$SNAP/microk8s-helm3.wrapper" install inaccel fpga-operator \
  --namespace kube-system \
  --repo https://setup.inaccel.com/helm \
  --set kubelet=$SNAP_COMMON/var/lib/kubelet \
  $@

echo "InAccel is enabled"
