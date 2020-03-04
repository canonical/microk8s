#!/usr/bin/env bash

set -ex

source $SNAP/actions/common/utils.sh

echo "Enabling Knative"

# Knative require istio
"$SNAP/microk8s-enable.wrapper" istio

echo "Waiting for Istio to be ready"
JSONPATH='{range .items[*]}{range @.status.readyReplicas}{@}{"\n"}{end}{end}'

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
# Wait for all 12 Istio deployments to be ready.
while ! [ $($KUBECTL get deployments -n istio-system -o jsonpath="$JSONPATH" | grep 1 | wc -l) -eq 12 ]
do
    echo -n "."
    sleep 2
done

echo
echo "Installing Knative CRDs"
n=0
until [ $n -ge 10 ]
do
  sleep 3
  ($KUBECTL apply --selector knative.dev/crd-install=true \
    -f ${SNAP}/actions/knative/serving.yaml \
    -f ${SNAP}/actions/knative/release.yaml \
    -f ${SNAP}/actions/knative/monitoring.yaml) && break
  n=$[$n+1]
  if [ $n -ge 10 ]; then
    echo "Knative failed to install"
    exit 1
  fi
done

echo "Installing Knative dependencies"
n=0
until [ $n -ge 10 ]
do
  sleep 3
  ($KUBECTL apply  \
    -f ${SNAP}/actions/knative/serving.yaml \
    -f ${SNAP}/actions/knative/release.yaml \
    -f ${SNAP}/actions/knative/monitoring.yaml) && break
  n=$[$n+1]
  if [ $n -ge 10 ]; then
    echo "Knative failed to install"
    exit 1
  fi
done

echo "Knative is starting"
