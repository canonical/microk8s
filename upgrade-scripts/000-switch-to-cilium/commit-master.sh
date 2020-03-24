#!/bin/bash
set -e

echo "Switching master to cilium"

source $SNAP/actions/common/utils.sh
CA_CERT=/snap/core/current/etc/ssl/certs/ca-certificates.crt

RESOURCES="$SNAP/upgrade-scripts/000-switch-to-cilium/resources"

run_with_sudo mv "$SNAP_DATA/args/cni-network/cni.conf" "$SNAP_DATA/args/cni-network/10-kubenet.conf" 2>/dev/null || true
run_with_sudo mv "$SNAP_DATA/args/cni-network/flannel.conflist" "$SNAP_DATA/args/cni-network/20-flanneld.conflist" 2>/dev/null || true
run_with_sudo cp "$RESOURCES/05-cilium-cni.conf" "$SNAP_DATA/args/cni-network/"
run_with_sudo cp "$RESOURCES/cilium.yaml" "$SNAP_DATA/args/cni-network/"
run_with_sudo mkdir -p "$SNAP_DATA/opt/cni/bin/"
run_with_sudo cp -R "$SNAP"/opt/cni/bin/* "$SNAP_DATA"/opt/cni/bin/

echo "Restarting kube-apiserver"
refresh_opt_in_config "allow-privileged" "true" kube-apiserver
run_with_sudo systemctl restart snap.${SNAP_NAME}.daemon-apiserver

# Reconfigure kubelet/containerd to pick up the new CNI config and binary.
echo "Restarting kubelet"
refresh_opt_in_config "cni-bin-dir" "\${SNAP_DATA}/opt/cni/bin/" kubelet
run_with_sudo systemctl restart snap.${SNAP_NAME}.daemon-kubelet

set_service_not_expected_to_start flanneld
run_with_sudo systemctl stop snap.${SNAP_NAME}.daemon-flanneld
remove_vxlan_interfaces

if grep -qE "bin_dir.*SNAP}\/" $SNAP_DATA/args/containerd-template.toml; then
  echo "Restarting containerd"
  run_with_sudo "${SNAP}/bin/sed" -i 's;bin_dir = "${SNAP}/opt;bin_dir = "${SNAP_DATA}/opt;g' "$SNAP_DATA/args/containerd-template.toml"
  run_with_sudo systemctl restart snap.${SNAP_NAME}.daemon-containerd
fi

${SNAP}/microk8s-status.wrapper --wait-ready --timeout 30

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
$KUBECTL apply -f "$SNAP_DATA/args/cni-network/cilium.yaml"

echo "Cilium is enabled"
