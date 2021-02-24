#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh
CA_CERT=/snap/core18/current/etc/ssl/certs/ca-certificates.crt

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

do_prerequisites() {
  refresh_opt_in_config "authentication-token-webhook" "true" kubelet
  restart_service kubelet
  # enable dns service
  "$SNAP/microk8s-enable.wrapper" dns
  # Allow some time for the apiserver to start
  sleep 5
  ${SNAP}/microk8s-status.wrapper --wait-ready --timeout 30 >/dev/null
}


get_kube_prometheus () {
  if [  ! -d "${SNAP_DATA}/kube-prometheus" ]
  then
    KUBE_PROMETHEUS_VERSION="v0.6.0"
    KUBE_PROMETHEUS_ERSION=$(echo $KUBE_PROMETHEUS_VERSION | sed 's/v//g')
    echo "Fetching kube-prometheus version $KUBE_PROMETHEUS_VERSION."
    run_with_sudo mkdir -p "${SNAP_DATA}/kube-prometheus"
    run_with_sudo mkdir -p "${SNAP_DATA}/tmp/kube-prometheus"

    run_with_sudo "${SNAP}/usr/bin/curl" --cacert $CA_CERT -L https://github.com/prometheus-operator/kube-prometheus/archive/${KUBE_PROMETHEUS_VERSION}.tar.gz -o "$SNAP_DATA/tmp/kube-prometheus/kube-prometheus.tar.gz"
    run_with_sudo tar -xzvf "$SNAP_DATA/tmp/kube-prometheus/kube-prometheus.tar.gz" -C "$SNAP_DATA/tmp/kube-prometheus/"
    run_with_sudo cp -R "$SNAP_DATA/tmp/kube-prometheus/kube-prometheus-${KUBE_PROMETHEUS_ERSION}/manifests/" "${SNAP_DATA}/kube-prometheus"

    run_with_sudo rm -rf "$SNAP_DATA/tmp/kube-prometheus"
  fi
}

use_multiarch_images() {
  # Use multi-arch kube-state-metrics
  run_with_sudo $SNAP/bin/sed -i 's@quay.io/coreos/kube-state-metrics:v1.9.5@gcr.io/k8s-staging-kube-state-metrics/kube-state-metrics:v1.9.7@g' ${SNAP_DATA}/kube-prometheus/manifests/kube-state-metrics-deployment.yaml
  # use kube-rbac-proxy multi-arch
  # This is the same image used in the master branch of kube-prometheus
  run_with_sudo $SNAP/bin/sed -i 's@quay.io/coreos/kube-rbac-proxy:v0.4.1@quay.io/brancz/kube-rbac-proxy:v0.8.0@g' ${SNAP_DATA}/kube-prometheus/manifests/kube-state-metrics-deployment.yaml
  run_with_sudo $SNAP/bin/sed -i 's@quay.io/coreos/kube-rbac-proxy:v0.4.1@quay.io/brancz/kube-rbac-proxy:v0.8.0@g' ${SNAP_DATA}/kube-prometheus/manifests/node-exporter-daemonset.yaml
  run_with_sudo $SNAP/bin/sed -i 's@quay.io/coreos/kube-rbac-proxy:v0.4.1@quay.io/brancz/kube-rbac-proxy:v0.8.0@g' ${SNAP_DATA}/kube-prometheus/manifests/setup/prometheus-operator-deployment.yaml
}


set_replicas_to_one() {
  # alert manager must be set to 1 replica
  run_with_sudo $SNAP/bin/sed -i 's@replicas: .@replicas: 1@g' ${SNAP_DATA}/kube-prometheus/manifests/alertmanager-alertmanager.yaml
  # prometheus must be set to 1 replica
  run_with_sudo $SNAP/bin/sed -i 's@replicas: .@replicas: 1@g' ${SNAP_DATA}/kube-prometheus/manifests/prometheus-prometheus.yaml

}

enable_prometheus() {
  echo "Enabling Prometheus"
  $KUBECTL apply -f "${SNAP_DATA}/kube-prometheus/manifests/setup"
  n=0
  until [ $n -ge 10 ]
  do
    sleep 3
    ($KUBECTL apply -f "${SNAP_DATA}/kube-prometheus/manifests/") && break
    n=$[$n+1]
    if [ $n -ge 10 ]; then
      echo "The Prometheus operator failed to install"
      exit 1
    fi
done 
}

do_prerequisites
get_kube_prometheus
set_replicas_to_one
use_multiarch_images
enable_prometheus

echo "The Prometheus operator is enabled (user/pass: admin/admin)"
