#!/usr/bin/env bash

set -e

source "${SNAP}/actions/common/utils.sh"

KUBECTL="${SNAP}/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

if [ -f "${SNAP_DATA}/args/cni-network/00-multus.conf" ]
then
  echo "Disabling Multus"
  echo "Checking if multus daemonset is running"
  DS_CHECK=$(${KUBECTL} get pods -n kube-system --selector=app=multus -o name)
  if [ -n "${DS_CHECK}" ]; then
    echo "Found multus deamonset, removing it and cleaning up OS files"
    cat "${SNAP}/actions/multus.yaml" | ${SNAP}/bin/sed "s#{{SNAP_DATA}}#${SNAP_DATA}#g" | ${KUBECTL} delete -f - 
    run_with_sudo rm -f "${SNAP_DATA}/args/cni-network/00-multus.conf"
    run_with_sudo rm -rf "${SNAP_DATA}/args/cni-network/multus.d"
    run_with_sudo rm -f "${SNAP_DATA}/opt/cni/bin/multus"

    echo -n "Waiting for multus daemonset to terminate."
    while [ -n "${DS_CHECK}" ]; do
      sleep 3
      DS_CHECK=$(${KUBECTL} get pods -n kube-system --selector=app=multus -o name)
      echo -n "."
    done 
    echo
    echo "Multus daemonset terminated."
    echo "Initiating removal on all other nodes."
    nodes_addon multus disable
  else
    echo "Daemonset not found so we are likely a node, cleaning up OS files"
    run_with_sudo rm -f "${SNAP_DATA}/args/cni-network/00-multus.conf"
    run_with_sudo rm -rf "${SNAP_DATA}/args/cni-network/multus.d"
    run_with_sudo rm -f "${SNAP_DATA}/opt/cni/bin/multus"
  fi
  echo "Multus is disabled"
else
  echo "Multus is not installed."
fi
