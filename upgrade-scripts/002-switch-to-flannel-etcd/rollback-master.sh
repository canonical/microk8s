#!/bin/bash
set -ex

echo "Rolling back dqlite upgrade on master"

source $SNAP/actions/common/utils.sh
CA_CERT=/snap/core/current/etc/ssl/certs/ca-certificates.crt
BACKUP_DIR="$SNAP_DATA/var/tmp/upgrades/002-switch-to-flannel-etcd"

${SNAP}/microk8s-stop.wrapper

echo "Restarting etcd"
set_service_not_expected_to_start etcd
if [ -e "$BACKUP_DIR/args/etcd" ]; then
  cp "$BACKUP_DIR"/args/etcd "$SNAP_DATA/args/"
fi

echo "Restarting kube-apiserver"
if [ -e "$BACKUP_DIR/args/kube-apiserver" ]; then
  cp "$BACKUP_DIR"/args/kube-apiserver "$SNAP_DATA/args/"
fi

set_service_not_expected_to_start flanneld
if [ -e "$BACKUP_DIR/args/cni-network" ]; then
  find "$SNAP_DATA"/args/cni-network/* -not -name '*multus*' -exec rm -f {} \;
  cp -rf "$BACKUP_DIR"/args/cni-network/* "$SNAP_DATA/args/cni-network/"
fi

chmod -R ug+rwX "${SNAP_DATA}/args/"
chmod -R o-rwX "${SNAP_DATA}/args/"
if getent group microk8s >/dev/null 2>&1
then
  chgrp microk8s -R ${SNAP_DATA}/args/ || true
fi

${SNAP}/microk8s-start.wrapper || true
${SNAP}/microk8s-status.wrapper --wait-ready --timeout 30

if [ -e "$SNAP_DATA/args/cni-network/cni.yaml" ]; then
  KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
  $KUBECTL apply -f "$SNAP_DATA/args/cni-network/cni.yaml"
fi

echo "Flannle-etcd rolled back"
