#!/bin/bash
set -ex

echo "Rolling back calico upgrade on a node"

source $SNAP/actions/common/utils.sh
CA_CERT=/snap/core/current/etc/ssl/certs/ca-certificates.crt

BACKUP_DIR="$SNAP_DATA/var/tmp/upgrades/000-switch-to-calico"

if [ -e "$BACKUP_DIR/args/cni-network/flannel.conflist" ]; then
  find "$SNAP_DATA"/args/cni-network/* -not -name '*multus*' -exec rm -f {} \;
  cp -rf "$BACKUP_DIR"/args/cni-network/* "$SNAP_DATA/args/cni-network/"
fi

echo "Restarting kubelet"
if [ -e "$BACKUP_DIR/args/kubelet" ]; then
  cp "$BACKUP_DIR"/args/kubelet "$SNAP_DATA/args/"
  snapctl restart ${SNAP_NAME}.daemon-kubelet
fi

echo "Restarting kube-proxy"
if [ -e "$BACKUP_DIR/args/kube-proxy" ]; then
  cp "$BACKUP_DIR"/args/kube-proxy "$SNAP_DATA/args/"
  snapctl restart ${SNAP_NAME}.daemon-proxy
fi

echo "Restarting kube-apiserver"
if [ -e "$BACKUP_DIR/args/kube-apiserver" ]; then
  cp "$BACKUP_DIR"/args/kube-apiserver "$SNAP_DATA/args/"
fi


echo "Restarting flannel"
set_service_expected_to_start flanneld
remove_vxlan_interfaces
snapctl start ${SNAP_NAME}.daemon-flanneld

echo "Calico rolledback"
