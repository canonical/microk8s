#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

disable_old_prometheus() {
  echo "Disabling old Prometheus"
  $KUBECTL delete -f "${SNAP}/actions/prometheus" > /dev/null 2>&1 || true
  $KUBECTL delete -f "${SNAP}/actions/prometheus/setup" > /dev/null 2>&1 || true
}

disable_kube_prometheus() {
  echo "Disabling Prometheus"
  $KUBECTL delete -f "${SNAP_DATA}/kube-prometheus/manifests/"
  $KUBECTL delete -f "${SNAP_DATA}/kube-prometheus/manifests/setup"
  run_with_sudo rm -rf "${SNAP_DATA}/kube-prometheus"
}

disable_old_prometheus
disable_kube_prometheus

echo "The Prometheus operator is disabled"
