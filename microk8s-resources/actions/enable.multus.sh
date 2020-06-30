#!/usr/bin/env bash

set -e

source "${SNAP}/actions/common/utils.sh"

KUBECTL="${SNAP}/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

echo "Enabling Multus"

if [ -f "${SNAP_DATA}/args/cni-network/00-multus.conf" ]
then
  echo "Multus is already installed."
else
  echo "Waiting for microk8s to be ready."
  "${SNAP}/microk8s-status.wrapper" --wait-ready >/dev/null

  echo "Applying manifest for multus daemonset."
  cat "${SNAP}/actions/multus.yaml" | "${SNAP}/bin/sed" "s#{{SNAP_DATA}}#${SNAP_DATA}#g" | ${KUBECTL} apply -f -

  echo -n "Waiting for multus daemonset to start."
  until [ -f "${SNAP_DATA}/opt/cni/bin/multus" ]; do
    sleep 1
    echo -n "."
  done
  echo
  echo "Multus is enabled"
fi

echo "Multus is enabled with version:"
"${SNAP_DATA}/opt/cni/bin/multus" -v

echo
echo "Currently installed CNI and IPAM plugins include:"
echo $(cd "${SNAP_DATA}/opt/cni/bin/"; ls)

echo
echo "New CNI plugins can be installed in ${SNAP_DATA}/opt/cni/bin/"

echo
echo "For information on configuration please refer to the multus documentation."
echo "  First you need to create network definitions:"
echo "    https://github.com/intel/multus-cni/blob/master/doc/how-to-use.md#create-network-attachment-definition"
echo "  Then you need to tell your pods to use those networks via annotations"
echo "    https://github.com/intel/multus-cni/blob/master/doc/how-to-use.md#run-pod-with-network-annotation"
echo
