#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling default storage class"
run_with_sudo mkdir -p ${SNAP_COMMON}/default-storage

"$SNAP/microk8s-enable.wrapper" dns
"$SNAP/microk8s-enable.wrapper" helm3

"$SNAP/microk8s-helm3.wrapper" repo add rimusz https://charts.rimusz.net
"$SNAP/microk8s-helm3.wrapper" repo update
"$SNAP/microk8s-helm3.wrapper" install hostpath-provisioner rimusz/hostpath-provisioner \
  --namespace kube-system \
  --version=0.2.13 \
  --set nodeHostPath=${SNAP_COMMON}/default-storage

echo "Storage will be available soon"

if [ -e ${SNAP_DATA}/var/lock/clustered.lock ]
then
  echo ""
  echo "WARNING: The storage class enabled does not persist volumes across nodes"
  echo ""
fi
