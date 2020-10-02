#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

disable_old_prometheus() {
  echo "Disabling old Prometheus"
  $KUBECTL delete -f "${SNAP}/actions/prometheus/deprecated" || true
  $KUBECTL delete -f "${SNAP}/actions/prometheus/deprecated/setup" || true
}

disable_kube_prometheus() {

  if [ -d "${SNAP_DATA}/kube-prometheus/manifests/" ]
  then
    echo "Disabling Prometheus"
    $KUBECTL delete -f "${SNAP_DATA}/kube-prometheus/manifests/" || true
    $KUBECTL delete -f "${SNAP_DATA}/kube-prometheus/manifests/setup" || true
    run_with_sudo rm -rf "${SNAP_DATA}/kube-prometheus"
  else
    disable_old_prometheus
  fi
}

disable_kube_prometheus

echo "The Prometheus operator is disabled"
