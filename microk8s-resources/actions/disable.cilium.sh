#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Cilium"

"$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" delete -f "$SNAP_DATA/actions/cilium.yaml"

# Give K8s some time to process the deletion request
sleep 15
cilium=$(wait_for_service_shutdown "kube-system" "k8s-app=cilium")
if [[ $cilium == fail ]]
then
  echo "Cilium did not shut down on time. Proceeding."
fi

cilium=$(wait_for_service_shutdown "kube-system" "name=cilium-operator")
if [[ $cilium == fail ]]
then
  echo "Cilium operator did not shut down on time. Proceeding."
fi
run_with_sudo rm -f "$SNAP_DATA/args/cni-network/05-cilium-cni.conf"
run_with_sudo rm -f "$SNAP_DATA/opt/cni/bin/cilium-cni"
run_with_sudo rm -rf $SNAP_DATA/bin/cilium*
run_with_sudo rm -f "$SNAP_DATA/actions/cilium.yaml"
run_with_sudo rm -rf "$SNAP_DATA/actions/cilium"
run_with_sudo rm -rf "$SNAP_DATA/var/run/cilium"
run_with_sudo rm -rf "$SNAP_DATA/sys/fs/bpf"

if $SNAP/sbin/ip link show "cilium_vxlan"
then
  echo "Deleting old cilium_vxlan link"
  run_with_sudo $SNAP/sbin/ip link delete "cilium_vxlan"
fi

set_service_expected_to_start flanneld

echo "Restarting flanneld"
run_with_sudo preserve_env snapctl stop "${SNAP_NAME}.daemon-flanneld"

echo "Cilium is terminating"
