#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Knative"


KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

declare -a yamls=("https://github.com/knative/serving/releases/download/knative-v1.2.0/serving-core.yaml"
                  "https://github.com/knative-sandbox/net-kourier/releases/download/knative-v1.2.0/kourier.yaml"
                  "https://github.com/knative/serving/releases/download/knative-v1.2.0/serving-default-domain.yaml"
                  "https://github.com/knative/eventing/releases/download/knative-v1.2.0/eventing-core.yaml"
                  "https://github.com/knative/eventing/releases/download/knative-v1.2.0/in-memory-channel.yaml"
                  "https://github.com/knative/eventing/releases/download/knative-v1.2.0/mt-channel-broker.yaml"
                  "https://github.com/knative/serving/releases/download/knative-v1.2.0/serving-crds.yaml"
                  "https://github.com/knative/eventing/releases/download/knative-v1.2.0/eventing-crds.yaml"
                 )

for yaml in "${yamls[@]}"
do
   $KUBECTL apply -f "$yaml"
   sleep 3
done

# Configure knative serving to use kourier as default networking layer, user can change it later to istio or contour
$KUBECTL patch configmap/config-network --namespace knative-serving --type merge --patch '{"data":{"ingress.class":"kourier.ingress.networking.knative.dev"}}'

echo ""
echo ""
echo "Visit https://knative.dev/docs/install/ for more customizations for knative"
echo ""
