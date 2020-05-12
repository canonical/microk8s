#!/usr/bin/env bash

set -eu

export PATH="$SNAP/usr/sbin:$SNAP/usr/bin:$SNAP/sbin:$SNAP/bin:$PATH"
ARCH="$($SNAP/bin/uname -m)"
export IN_SNAP_LD_LIBRARY_PATH="$SNAP/lib:$SNAP/usr/lib:$SNAP/lib/$ARCH-linux-gnu:$SNAP/usr/lib/$ARCH-linux-gnu"

source $SNAP/actions/common/utils.sh

exit_if_no_permissions

workers=$("$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" get no | grep " Ready" | wc -l)

run_with_sudo mkdir -p ${SNAP_DATA}/var/log/
echo "Enabling HA"
echo "Upgrading the network CNI"
run_with_sudo preserve_env LD_LIBRARY_PATH=$IN_SNAP_LD_LIBRARY_PATH ${SNAP}/usr/bin/python3 ${SNAP}/scripts/wrappers/upgrade.py -r 000-switch-to-calico 2>&1 | run_with_sudo tee ${SNAP_DATA}/var/log/ha-cluster-upgrade.log &>/dev/null
if [ $? -ne 0 ]; then
  echo "CNI upgrade failed. Please see logs at ${SNAP_DATA}/var/log/ha-cluster-upgrade.log for more details."
  echo "HA configuration aborted"
  exit 1
fi

echo "Waiting for the cluster to restart"
${SNAP}/microk8s-status.wrapper --wait-ready --timeout 60 &>/dev/null

echo "Waiting for the CNI to deploy"
"$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" -n kube-system rollout status ds/calico-node
"$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" -n kube-system rollout status deployment/calico-kube-controllers

echo "Configuring the datastore"
run_with_sudo preserve_env LD_LIBRARY_PATH=$IN_SNAP_LD_LIBRARY_PATH ${SNAP}/usr/bin/python3 ${SNAP}/scripts/wrappers/upgrade.py -r 001-switch-to-dqlite 2>&1 | run_with_sudo tee -a ${SNAP_DATA}/var/log/ha-cluster-upgrade.log &>/dev/null
if [ $? -ne 0 ]; then
  echo "Datastore upgrade failed. Please see logs at ${SNAP_DATA}/var/log/ha-cluster-upgrade.log for more details."
  echo "HA configuration aborted"
  exit 1
fi

echo "Waiting for the cluster to start with the new datastore"
${SNAP}/microk8s-status.wrapper --wait-ready --timeout 60 &>/dev/null

touch "${SNAP_DATA}/var/lock/ha-cluster"

echo
echo "The node is now HA ready. Join three or more nodes to form an HA cluster."
echo
if [ "$workers" -ge "2" ]; then
  echo "The worker nodes already joined to this master need to be removed them and re-joined."
fi
