#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Fluentd-Elasticsearch"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

NODENAME="$($KUBECTL get no -o yaml | grep " name:"| awk '{print $2}')"

# This one deletes the old fluentd configmap.
$KUBECTL -n kube-system delete cm fluentd-es-config-v0.1.5 || true
$KUBECTL -n kube-system delete daemonset fluentd-es-v2.2.0 || true

$KUBECTL label nodes "$NODENAME" beta.kubernetes.io/fluentd-ds-ready- || true

$KUBECTL delete -f "${SNAP}/actions/fluentd"
# Allow for a few seconds for the deletion to take place
sleep 10

echo "Fluentd-Elasticsearch is disabled"
