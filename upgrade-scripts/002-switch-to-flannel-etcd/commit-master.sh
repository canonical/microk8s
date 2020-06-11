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
skip_opt_in_config "storage-backend" kube-apiserver
skip_opt_in_config "storage-dir" kube-apiserver
refresh_opt_in_config "etcd-servers" 'https://127.0.0.1:12379' kube-apiserver
refresh_opt_in_config "etcd-cafile" "\${SNAP_DATA}/certs/ca.crt" kube-apiserver
refresh_opt_in_config "etcd-certfile" "\${SNAP_DATA}/certs/server.crt" kube-apiserver
refresh_opt_in_config "etcd-keyfile" "\${SNAP_DATA}/certs/server.key" kube-apiserver

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
