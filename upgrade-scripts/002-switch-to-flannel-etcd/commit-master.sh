#!/bin/bash
set -ex

echo "Switching master to dqlite"

source $SNAP/actions/common/utils.sh
CA_CERT=/snap/core/current/etc/ssl/certs/ca-certificates.crt

BACKUP_DIR="$SNAP_DATA/var/tmp/upgrades/002-switch-to-flannel-etcd"
DB_DIR="$BACKUP_DIR/db"

mkdir -p "$BACKUP_DIR/args/"

if [ -e "$SNAP_DATA/args/cni-network/cni.yaml" ]; then
  KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
  $KUBECTL delete -f "$SNAP_DATA/args/cni-network/cni.yaml" || true
  sleep 10
fi

echo "Configuring services"
${SNAP}/microk8s-stop.wrapper

cp "$SNAP_DATA"/args/kube-apiserver "$BACKUP_DIR/args"

"${SNAP}/bin/sed" -i '/--storage-backend/d' "$SNAP_DATA/args/kube-apiserver"
"${SNAP}/bin/sed" -i '/--storage-dir/d' "$SNAP_DATA/args/kube-apiserver"

echo "--etcd-servers=https://127.0.0.1:12379" >> "$SNAP_DATA/args/kube-apiserver"
echo "--etcd-cafile=\${SNAP_DATA}/certs/ca.crt" >> "$SNAP_DATA/args/kube-apiserver"
echo "--etcd-certfile=\${SNAP_DATA}/certs/server.crt" >> "$SNAP_DATA/args/kube-apiserver"
echo "--etcd-keyfile=\${SNAP_DATA}/certs/server.key" >> "$SNAP_DATA/args/kube-apiserver"

cp "$SNAP_DATA"/args/etcd "$BACKUP_DIR/args"
rm -rf ${SNAP_COMMON}/var/run/etcd/*
cp "$SNAP"/default-args/etcd "$SNAP_DATA"/args/
chmod 660 "$SNAP_DATA"/args/etcd

cp -r "$SNAP_DATA"/args/cni-network "$BACKUP_DIR/args/"
find "$SNAP_DATA"/args/cni-network/* -not -name '*multus*' -exec rm -f {} \;
cp "$SNAP"/default-args/cni-network/* "$SNAP_DATA"/args/cni-network/
chmod -R 660 "$SNAP_DATA"/args/cni-network

if getent group microk8s >/dev/null 2>&1
then
  chgrp microk8s -R ${SNAP_DATA}/args/ || true
fi

set_service_expected_to_start etcd
set_service_expected_to_start flanneld

${SNAP}/microk8s-start.wrapper
${SNAP}/microk8s-status.wrapper --wait-ready --timeout 30

echo "Switch to etcd and flanneld completed"
