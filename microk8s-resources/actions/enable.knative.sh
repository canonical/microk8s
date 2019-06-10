#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Knative"

# Knative require istio
"$SNAP/microk8s-enable.wrapper" istio

echo "Waiting for Istio to be ready"
JSONPATH='{range .items[*]}{range @.status.readyReplicas}{@}{"\n"}{end}{end}'

# Wait for all 12 Istio deployments to be ready.
while ! [ $($SNAP/kubectl get deployments -n istio-system -o jsonpath="$JSONPATH" | grep 1 | wc -l) -eq 12 ]
do
    echo -n "."
    sleep 2
done

echo
echo "Installing Knative CRDs"
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply --selector knative.dev/crd-install=true \
-f ${SNAP}/actions/knative/serving.yaml \
-f ${SNAP}/actions/knative/build.yaml \
-f ${SNAP}/actions/knative/release.yaml \
-f ${SNAP}/actions/knative/eventing-sources.yaml \
-f ${SNAP}/actions/knative/monitoring.yaml \
-f ${SNAP}/actions/knative/clusterrole.yaml

echo "Installing Knative dependencies"
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply  \
-f ${SNAP}/actions/knative/serving.yaml \
-f ${SNAP}/actions/knative/build.yaml \
-f ${SNAP}/actions/knative/release.yaml \
-f ${SNAP}/actions/knative/eventing-sources.yaml \
-f ${SNAP}/actions/knative/monitoring.yaml \
-f ${SNAP}/actions/knative/clusterrole.yaml

echo "Knative is starting"
