#!/bin/bash
set -ex

echo "Rolling back dqlite upgrade on master"

source $SNAP/actions/common/utils.sh
CA_CERT=/snap/core/current/etc/ssl/certs/ca-certificates.crt
BACKUP_DIR="$SNAP_DATA/var/tmp/upgrades/001-switch-to-dqlite"

echo "Restarting etcd"
set_service_expected_to_start etcd
if [ -e "$BACKUP_DIR/args/etcd" ]; then
  cp "$BACKUP_DIR"/args/etcd "$SNAP_DATA/args/"
  snapctl restart ${SNAP_NAME}.daemon-etcd
fi

echo "Restarting kube-apiserver"
if [ -e "$BACKUP_DIR/args/kube-apiserver" ]; then
  cp "$BACKUP_DIR"/args/kube-apiserver "$SNAP_DATA/args/"
  snapctl restart ${SNAP_NAME}.daemon-apiserver
fi

${SNAP}/microk8s-start.wrapper
${SNAP}/microk8s-status.wrapper --wait-ready --timeout 30

echo "Dqlite rolled back"
