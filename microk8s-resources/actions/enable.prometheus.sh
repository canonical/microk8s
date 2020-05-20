#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Prometheus"
refresh_opt_in_config "authentication-token-webhook" "true" kubelet
restart_service kubelet

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
$KUBECTL apply -f "${SNAP}/actions/prometheus/setup"

n=0
until [ $n -ge 10 ]
do
  sleep 3
  ($KUBECTL apply -f "${SNAP}/actions/prometheus/") && break
  n=$[$n+1]
  if [ $n -ge 10 ]; then
    echo "The Prometheus operator failed to install"
    exit 1
  fi
done

echo "The Prometheus operator is enabled (user/pass: admin/admin)"
