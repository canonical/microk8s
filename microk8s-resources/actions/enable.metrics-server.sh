#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Metrics-Server"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
use_manifest metrics-server apply

refresh_opt_in_config "authentication-token-webhook" "true" kubelet
run_with_sudo preserve_env snapctl restart "${SNAP_NAME}.daemon-kubelet"

echo "Metrics-Server is enabled"
