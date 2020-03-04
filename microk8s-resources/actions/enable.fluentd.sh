#!/usr/bin/env bash

set -ex

export PATH="$SNAP/usr/sbin:$SNAP/usr/bin:$SNAP/sbin:$SNAP/bin:$PATH"

source $SNAP/actions/common/utils.sh

echo "Enabling Fluentd-Elasticsearch"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
echo "Labeling nodes"
NODENAME="$($KUBECTL get no -o yaml | grep " name:"| awk '{print $2}')"
for NODE in $NODENAME
do
  $KUBECTL label nodes "$NODE" beta.kubernetes.io/fluentd-ds-ready=true || true
done

"$SNAP/microk8s-enable.wrapper" dns
sleep 5

$KUBECTL apply -f "${SNAP}/actions/fluentd"

echo "Fluentd-Elasticsearch is enabled"
