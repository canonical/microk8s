#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

disable_keda() {

  if [ -f "${SNAP_DATA}/keda/keda.yaml" ]
  then
    echo "Disabling KEDA"
    $KUBECTL delete -f "${SNAP_DATA}/keda/keda.yaml" || true
    rm -rf "${SNAP_DATA}/keda"
  fi
}

disable_keda

echo "The KEDA addon is disabled."
