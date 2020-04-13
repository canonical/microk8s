#!/bin/bash
set -e

echo "Rolling back cilium upgrade on master"

source $SNAP/actions/common/utils.sh
CA_CERT=/snap/core/current/etc/ssl/certs/ca-certificates.crt


KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
$KUBECTL delete -f "$SNAP_DATA/args/cni-network/cilium.yaml"


if [ -e "$SNAP_DATA/args/cni-network/05-cilium-cni.conf" ]; then
  run_with_sudo mv "$SNAP_DATA/args/cni-network/20-flanneld.conflist" "$SNAP_DATA/args/cni-network/flannel.conflist" 2>/dev/null || true
  run_with_sudo rm -rf "$SNAP_DATA/args/cni-network/05-cilium-cni.conf"
  run_with_sudo rm -rf "$SNAP_DATA/args/cni-network/cilium.yaml"
fi

# Reconfigure kubelet/containerd to pick up the new CNI config and binary.
echo "Restarting kubelet"
refresh_opt_in_config "cni-bin-dir" "\${SNAP}/opt/cni/bin/" kubelet
run_with_sudo systemctl restart snap.${SNAP_NAME}.daemon-kubelet

${SNAP}/microk8s-status.wrapper --wait-ready --timeout 30

echo "Restarting flannel"
set_service_expected_to_start flanneld
remove_vxlan_interfaces
run_with_sudo systemctl start snap.${SNAP_NAME}.daemon-flanneld

echo "Restarting kubelet"
if grep -qE "bin_dir.*SNAP_DATA}\/" $SNAP_DATA/args/containerd-template.toml; then
  echo "Restarting containerd"
  run_with_sudo "${SNAP}/bin/sed" -i 's;bin_dir = "${SNAP_DATA}/opt;bin_dir = "${SNAP}/opt;g' "$SNAP_DATA/args/containerd-template.toml"
  run_with_sudo systemctl restart snap.${SNAP_NAME}.daemon-containerd
fi

echo "Cilium rolldback"
