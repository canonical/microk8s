#!/usr/bin/env bash

set -ex

source $SNAP/actions/common/utils.sh

echo "Disabling Fluentd-Elasticsearch"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

NODENAME="$($KUBECTL get no -o yaml | grep " name:"| awk '{print $2}')"

$KUBECTL label nodes "$NODENAME" beta.kubernetes.io/fluentd-ds-ready- || true

$KUBECTL delete -f "${SNAP}/actions/fluentd"

echo "Fluentd-Elasticsearch is disabled"
