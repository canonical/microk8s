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
sudo rm -f "$SNAP_DATA/args/cni-network/05-cilium-cni.conf"
sudo rm -f "$SNAP_DATA/opt/cni/bin/cilium-cni"
sudo rm -rf $SNAP_DATA/bin/cilium*
sudo rm -f "$SNAP_DATA/actions/cilium.yaml"
sudo rm -rf "$SNAP_DATA/actions/cilium"
sudo rm -rf "$SNAP_DATA/var/run/cilium"
sudo rm -rf "$SNAP_DATA/sys/fs/bpf"

if $SNAP/sbin/ip link show "cilium_vxlan"
then
  echo "Deleting old cilium_vxlan link"
  sudo $SNAP/sbin/ip link delete "cilium_vxlan"
fi

set_service_expected_to_start flanneld

echo "Restarting kubelet"
refresh_opt_in_config "cni-bin-dir" "\${SNAP}/opt/cni/bin/" kubelet
sudo systemctl restart snap.${SNAP_NAME}.daemon-kubelet
echo "Restarting containerd"
if ! grep -qE "bin_dir.*SNAP}\/" $SNAP_DATA/args/containerd-template.toml; then
  sudo "${SNAP}/bin/sed" -i 's;bin_dir = "${SNAP_DATA}/opt;bin_dir = "${SNAP}/opt;g' "$SNAP_DATA/args/containerd-template.toml"
fi
sudo systemctl restart snap.${SNAP_NAME}.daemon-containerd

echo "Restarting flanneld"
sudo systemctl stop snap.${SNAP_NAME}.daemon-flanneld

echo "Cilium is terminating"
