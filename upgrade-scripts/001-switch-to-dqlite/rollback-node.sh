#!/bin/bash
set -ex

echo "Rolling back dqlite upgrade on master"

source $SNAP/actions/common/utils.sh
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
fi

snapctl restart ${SNAP_NAME}.daemon-kubelite

${SNAP}/microk8s-start.wrapper

echo "Dqlite rolled back"
