#!/bin/bash
set -e

echo "Switching master to calico"

source $SNAP/actions/common/utils.sh
CA_CERT=/snap/core/current/etc/ssl/certs/ca-certificates.crt

RESOURCES="$SNAP/upgrade-scripts/000-switch-to-calico/resources"
BACKUP_DIR="$SNAP_DATA/var/tmp/upgrades/000-switch-to-calico"

mkdir -p "$BACKUP_DIR"

mkdir -p "$BACKUP_DIR/args/cni-network/"
cp "$SNAP_DATA"/args/cni-network/* "$BACKUP_DIR/args/cni-network/" 2>/dev/null || true
rm -rf "$SNAP_DATA"/args/cni-network/*
cp "$RESOURCES/calico.yaml" "$SNAP_DATA/args/cni-network/cni.yaml"
mkdir -p "$SNAP_DATA/opt/cni/bin/"
cp -R "$SNAP"/opt/cni/bin/* "$SNAP_DATA"/opt/cni/bin/

echo "Restarting services"
cp "$SNAP_DATA"/args/kube-apiserver "$BACKUP_DIR/args"
refresh_opt_in_config "allow-privileged" "true" kube-apiserver
run_with_sudo systemctl restart snap.${SNAP_NAME}.daemon-apiserver

# Reconfigure kubelet/containerd to pick up the new CNI config and binary.
cp "$SNAP_DATA"/args/kubelet "$BACKUP_DIR/args"
echo "Restarting kubelet"
refresh_opt_in_config "cni-bin-dir" "\${SNAP_DATA}/opt/cni/bin/" kubelet
run_with_sudo systemctl restart snap.${SNAP_NAME}.daemon-kubelet

cp "$SNAP_DATA"/args/kube-proxy "$BACKUP_DIR/args"
echo "Restarting kube proxy"
refresh_opt_in_config "cluster-cidr" "10.1.0.0/16" kube-proxy
run_with_sudo systemctl restart snap.${SNAP_NAME}.daemon-proxy

set_service_not_expected_to_start flanneld
run_with_sudo systemctl stop snap.${SNAP_NAME}.daemon-flanneld
remove_vxlan_interfaces

cp "$SNAP_DATA"/args/containerd-template.toml "$BACKUP_DIR/args"
if grep -qE "bin_dir.*SNAP}\/" $SNAP_DATA/args/containerd-template.toml; then
  echo "Restarting containerd"
  run_with_sudo "${SNAP}/bin/sed" -i 's;bin_dir = "${SNAP}/opt;bin_dir = "${SNAP_DATA}/opt;g' "$SNAP_DATA/args/containerd-template.toml"
  run_with_sudo systemctl restart snap.${SNAP_NAME}.daemon-containerd
fi

${SNAP}/microk8s-status.wrapper --wait-ready --timeout 30

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
$KUBECTL apply -f "$SNAP_DATA/args/cni-network/cni.yaml"

echo "Calico is enabled"
