#!/usr/bin/env bash

set -e

echo "Enabling the private registry"

"$SNAP/microk8s-enable.wrapper" storage

echo "Applying registry manifest"
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" "apply" "-f" "${SNAP}/actions/registry.yaml"

echo "The registry is enabled"
