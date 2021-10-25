#!/bin/bash

set -ex

echo "Switching node to dqlite"

source $SNAP/actions/common/utils.sh

BACKUP_DIR="$SNAP_DATA/var/tmp/upgrades/001-switch-to-dqlite"

mkdir -p "$BACKUP_DIR/args/"

echo "Configuring services"
cp "$SNAP_DATA"/args/kube-apiserver "$BACKUP_DIR/args"

if [ -e ${SNAP}/default-args/k8s-dqlite ]
then
  echo "Configuring the API server for dqlite"
  cp ${SNAP}/default-args/k8s-dqlite ${SNAP_DATA}/args/k8s-dqlite
  refresh_opt_in_config etcd-servers unix://\${SNAP_DATA}/var/kubernetes/backend/kine.sock:12379 kube-apiserver
  skip_opt_in_config storage-backend kube-apiserver
  skip_opt_in_config storage-dir kube-apiserver
else
  refresh_opt_in_config "storage-backend" "dqlite" kube-apiserver
  refresh_opt_in_config "storage-dir" "\${SNAP_DATA}/var/kubernetes/backend/" kube-apiserver
  skip_opt_in_config "etcd-servers" kube-apiserver
  skip_opt_in_config "etcd-cafile" kube-apiserver
  skip_opt_in_config "etcd-certfile" kube-apiserver
  skip_opt_in_config "etcd-keyfile" kube-apiserver
fi

if ! [ -e "${SNAP_DATA}/var/kubernetes/backend/cluster.key" ]
then
  init_cluster
fi

set_service_not_expected_to_start etcd
set_service_expected_to_start k8s-dqlite

${SNAP}/microk8s-stop.wrapper
sleep 5
${SNAP}/microk8s-start.wrapper

echo "Dqlite is enabled on the node"
