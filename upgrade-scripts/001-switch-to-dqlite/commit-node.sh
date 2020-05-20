#!/bin/bash

set -ex

echo "Switching node to dqlite"

source $SNAP/actions/common/utils.sh
CA_CERT=/snap/core/current/etc/ssl/certs/ca-certificates.crt

BACKUP_DIR="$SNAP_DATA/var/tmp/upgrades/001-switch-to-dqlite"

mkdir -p "$BACKUP_DIR/args/"

echo "Configuring services"
cp "$SNAP_DATA"/args/kube-apiserver "$BACKUP_DIR/args"
refresh_opt_in_config "storage-backend" "dqlite" kube-apiserver
refresh_opt_in_config "storage-dir" "\${SNAP_DATA}/var/kubernetes/backend/" kube-apiserver
skip_opt_in_config "etcd-servers" kube-apiserver
skip_opt_in_config "etcd-cafile" kube-apiserver
skip_opt_in_config "etcd-certfile" kube-apiserver
skip_opt_in_config "etcd-keyfile" kube-apiserver

if ! [ -e "${SNAP_DATA}/var/kubernetes/backend/cluster.key" ]
then
  init_cluster
fi

set_service_not_expected_to_start etcd

${SNAP}/microk8s-stop.wrapper
sleep 5
${SNAP}/microk8s-start.wrapper

echo "Dqlite is enabled on the node"
