#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Knative"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

declare -a yamls=("https://github.com/knative/serving/releases/download/knative-v1.2.0/serving-crds.yaml"
                  "https://github.com/knative/eventing/releases/download/knative-v1.2.0/eventing-crds.yaml"
                  "https://github.com/knative/serving/releases/download/knative-v1.2.0/serving-core.yaml"
                  "https://github.com/knative-sandbox/net-kourier/releases/download/knative-v1.2.0/kourier.yaml"
                  "https://github.com/knative/serving/releases/download/knative-v1.2.0/serving-default-domain.yaml"
                  "https://github.com/knative/eventing/releases/download/knative-v1.2.0/eventing-core.yaml"
                  "https://github.com/knative/eventing/releases/download/knative-v1.2.0/in-memory-channel.yaml"
                  "https://github.com/knative/eventing/releases/download/knative-v1.2.0/mt-channel-broker.yaml"
                 )

# || true is there to handle race conditions in deleting resources
for yaml in "${yamls[@]}"
do
   $KUBECTL delete -f "$yaml" 2>&1 > /dev/null || true
   sleep 3
done

echo "Knative is terminating"
