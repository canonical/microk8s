#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Fluentd-Elasticsearch"

NODENAME="$("$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" get no -o yaml | grep " name:"| awk '{print $2}')"

"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" label nodes "$NODENAME" beta.kubernetes.io/fluentd-ds-ready- || true

"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" delete -f "${SNAP}/actions/fluentd"

echo "Fluentd-Elasticsearch is disabled"
