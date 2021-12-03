#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling default storage"
read -ra ARGUMENTS <<< "$1"

"$SNAP/microk8s-helm3.wrapper" uninstall hostpath-provisioner --namespace kube-system

sleep 5

echo "Storage removed"
if [ ! -z "${ARGUMENTS[@]}" ] && [ "${ARGUMENTS[@]}" = "destroy-storage" ]
then
  run_with_sudo rm -rf "$SNAP_COMMON/default-storage"
  echo "Storage space reclaimed"
else
  read -p "Remove PVC storage at $SNAP_COMMON/default-storage ? (Y/N): " confirm && [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]] || exit 1
  run_with_sudo rm -rf "$SNAP_COMMON/default-storage"
  echo "Storage space reclaimed"
fi
