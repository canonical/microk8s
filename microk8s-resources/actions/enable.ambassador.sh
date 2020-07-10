#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

NAMESPACE_AMB="ambassador"

MANIFEST_VER="latest"

MANIFEST_CRD="https://github.com/datawire/ambassador-operator/releases/$MANIFEST_VER/download/ambassador-operator-crds.yaml"

MANIFEST_AMB="https://github.com/datawire/ambassador-operator/releases/$MANIFEST_VER/download/ambassador-operator-microk8s.yaml"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"


echo "Enabling Ambassador"

# make sure nginx ingress is not enabled
"$SNAP/microk8s-disable.wrapper" ingress > /dev/null 2>&1 || true

# the operator will start failing without dns
"$SNAP/microk8s-enable.wrapper" dns

# make sure the "ambassador" namespace exists
$KUBECTL create namespace "$NAMESPACE_AMB" > /dev/null 2>&1 || true

# load the CRD and wait for it to be installed
$KUBECTL apply -f "$MANIFEST_CRD"

# wait for the CRD to be ready (otherwise we cannot load the AmbassadorInstallation)
$KUBECTL wait --for condition=established --timeout=60s crd ambassadorinstallations.getambassador.io

# load the rest of the manifests, and wait for them to be ready
$KUBECTL apply -n "$NAMESPACE_AMB" -f "$MANIFEST_AMB"

# print a final help message
echo "Ambassador has been installed"
echo ""
echo "Ingresses annotated with 'kubernetes.io/ingress.class=ambassador' will be managed by Ambassador."
