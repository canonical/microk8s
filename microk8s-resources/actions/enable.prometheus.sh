#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Prometheus"
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply -f "${SNAP}/actions/prometheus/resources"

n=0
until [ $n -ge 10 ]
do
  sleep 3
  ("$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply -f "${SNAP}/actions/prometheus/") && break
  n=$[$n+1]
  if [ $n -ge 10 ]; then
    echo "The Prometheus operator failed to install"
    exit 1
  fi
done

echo "The Prometheus operator is enabled (user/pass: admin/admin)"
