#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

NAMESPACE_AMB="ambassador"

MANIFEST_VER="latest"

MANIFEST_CRD="https://github.com/datawire/ambassador-operator/releases/$MANIFEST_VER/download/ambassador-operator-crds.yaml"

MANIFEST_AMB="https://github.com/datawire/ambassador-operator/releases/$MANIFEST_VER/download/ambassador-operator-microk8s.yaml"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

KUBECTL_DELETE_ARGS="--wait=true --timeout=180s --ignore-not-found=true"

echo "Disabling Ambassador"

# remove the AmbassadorInstallation, so the Ambassador Operator will remove Ambassador
# we should wait until Ambassador is fully uninstalled before moving forward
$KUBECTL delete $KUBECTL_DELETE_ARGS -n $NAMESPACE_AMB ambassadorinstallation ambassador

# give some time to the operator for finishing the uninstallation
sleep 5

# unload the the manifests
$KUBECTL delete $KUBECTL_DELETE_ARGS -n $NAMESPACE_AMB -f "$MANIFEST_AMB" > /dev/null 2>&1
$KUBECTL delete $KUBECTL_DELETE_ARGS -n $NAMESPACE_AMB -f "$MANIFEST_CRD" > /dev/null 2>&1

# delete the "ambassador" namespace
$KUBECTL delete $KUBECTL_DELETE_ARGS namespace "$NAMESPACE_AMB" > /dev/null 2>&1 || true

echo "Ambassador is disabled"
