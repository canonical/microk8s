#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Knative"

"$SNAP/microk8s-enable.wrapper" istio

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

declare -a yamls=("https://github.com/knative/serving/releases/download/v0.21.0/serving-crds.yaml"
                  "https://github.com/knative/eventing/releases/download/v0.21.0/eventing-crds.yaml"
                  "https://github.com/knative/serving/releases/download/v0.21.0/serving-core.yaml"
                  "https://github.com/knative/net-istio/releases/download/v0.21.0/net-istio.yaml"
                  "https://github.com/knative/serving/releases/download/v0.21.0/serving-default-domain.yaml"
                  "https://github.com/knative/eventing/releases/download/v0.21.0/eventing-core.yaml"
                  "https://github.com/knative/eventing/releases/download/v0.21.0/in-memory-channel.yaml"
                  "https://github.com/knative/eventing/releases/download/v0.21.0/mt-channel-broker.yaml"
                 )

for yaml in "${yamls[@]}"
do
   $KUBECTL apply -f "$yaml"
   sleep 3
done

echo ""
echo ""
echo "Visit https://knative.dev/docs/install/any-kubernetes-cluster/ to customize which broker channel"
echo "implementation is used and to specify which configurations are used for which namespaces."
echo ""
