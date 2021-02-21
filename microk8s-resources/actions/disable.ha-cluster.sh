#!/usr/bin/env bash

set -eu

export PATH="$SNAP/usr/sbin:$SNAP/usr/bin:$SNAP/sbin:$SNAP/bin:$PATH"
export PYTHONNOUSERSITE=false
export PYTHONHOME="$SNAP/usr"
export PYTHONPATH="$SNAP/usr/lib/python3/dist-packages/"

source $SNAP/actions/common/utils.sh

exit_if_no_permissions

echo "Reverting to a non-HA setup"
"${SNAP}/microk8s-leave.wrapper"
${SNAP}/microk8s-status.wrapper --wait-ready --timeout 30 &>/dev/null

workers=$("$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" get no | grep " Ready" | wc -l)

run_with_sudo mkdir -p ${SNAP_DATA}/var/log/

echo "Enabling flanneld and etcd"
run_with_sudo preserve_env ${SNAP}/bin/python ${SNAP}/scripts/wrappers/upgrade.py -r 002-switch-to-flannel-etcd 2>&1 | run_with_sudo tee ${SNAP_DATA}/var/log/ha-cluster-disable.log &>/dev/null
if [ $? -ne 0 ]; then
  echo "Transition to flannel and etcd failed. Please see logs at ${SNAP_DATA}/var/log/ha-cluster-disable.log for more details."
  exit 1
fi

rm -rf "${SNAP_DATA}/var/lock/ha-cluster"
echo "HA disabled"
