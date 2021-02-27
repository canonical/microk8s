#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Fluentd-Elasticsearch"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

# This one deletes the old fluentd resources.
$KUBECTL -n kube-system delete cm fluentd-es-config-v0.1.5 > /dev/null 2>&1 || true
$KUBECTL -n kube-system delete daemonset fluentd-es-v2.2.0 > /dev/null 2>&1 || true
$KUBECTL -n kube-system delete daemonset fluentd-es-v3.0.2 > /dev/null 2>&1 || true

NODENAME="$($KUBECTL get no -o yaml | grep " name:"| awk '{print $2}')"

for NODE in $NODENAME
do
  $KUBECTL label nodes "$NODENAME" beta.kubernetes.io/fluentd-ds-ready- || true
done


$KUBECTL delete -f "${SNAP}/actions/fluentd"
# Allow for a few seconds for the deletion to take place
sleep 10

echo "Fluentd-Elasticsearch is disabled"
