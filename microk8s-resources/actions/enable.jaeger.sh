#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Jaeger"

"$SNAP/microk8s-enable.wrapper" dns ingress

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
$KUBECTL apply -f "${SNAP}/actions/jaeger/crds"

n=0
until [ $n -ge 10 ]
do
  sleep 3
  ($KUBECTL apply -f "${SNAP}/actions/jaeger/") && break
  n=$[$n+1]
  if [ $n -ge 10 ]; then
    echo "Jaeger operator failed to install"
    exit 1
  fi
done

echo "Jaeger is enabled"
