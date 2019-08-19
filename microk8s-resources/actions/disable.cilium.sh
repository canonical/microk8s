#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Cilium"

if [ -L "${SNAP_DATA}/bin/cilium" ]
then
  "$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" delete -f "$SNAP_DATA/actions/cilium.yaml"

  sudo rm -f "$SNAP_DATA/args/cni-network/05-cilium-cni.conf"
  sudo rm -f "$SNAP_DATA/opt/cni/bin/cilium-cni"
  sudo rm -rf $SNAP_DATA/bin/cilium*
  sudo rm -f "$SNAP_DATA/actions/cilium.yaml"
  sudo rm -rf "$SNAP_DATA/actions/cilium"
  sudo rm -rf "$SNAP_DATA/var/run/cilium"
  sudo rm -rf "$SNAP_DATA/sys/fs/bpf"

  echo "Restarting kubelet"
  refresh_opt_in_config "network-plugin" "kubenet" kubelet
  refresh_opt_in_config "cni-bin-dir" "\${SNAP}/opt/cni/bin/" kubelet
  sudo systemctl restart snap.${SNAP_NAME}.daemon-kubelet
  echo "Restarting containerd"
  if ! grep -qE "bin_dir.*SNAP}\/" $SNAP_DATA/args/containerd-template.toml; then
    sudo "${SNAP}/bin/sed" -i 's;bin_dir = "${SNAP_DATA}/opt;bin_dir = "${SNAP}/opt;g' "$SNAP_DATA/args/containerd-template.toml"
  fi
  sudo systemctl restart snap.${SNAP_NAME}.daemon-containerd

  echo "Cilium is terminating"
  cilium=$(wait_for_service_shutdown "kube-system" "k8s-app=cilium")
  if [[ $cilium == fail ]]
  then
    echo "Cilium did not shut down on time. Proceeding."
  fi
fi
