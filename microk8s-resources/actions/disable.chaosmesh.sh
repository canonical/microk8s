#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

NAMESPACE="chaos-testing"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

KUBECTL_DELETE_ARGS="--wait=true --timeout=180s --ignore-not-found=true"

echo "Disabling ChaosMesh"

# unload the the  crd


# delete the namespaces
$KUBECTL delete $KUBECTL_DELETE_ARGS namespace "$NAMESPACE" > /dev/null 2>&1 || true
$KUBECTL delete $KUBECTL_DELETE_ARGS crd \
    awschaos.chaos-mesh.org  \
    dnschaos.chaos-mesh.org  \
    gcpchaos.chaos-mesh.org  \
    httpchaos.chaos-mesh.org \
    iochaos.chaos-mesh.org   \
    jvmchaos.chaos-mesh.org  \
    kernelchaos.chaos-mesh.org \
    networkchaos.chaos-mesh.org \
    podhttpchaos.chaos-mesh.org \
    podiochaos.chaos-mesh.org \
    podnetworkchaos.chaos-mesh.org \
    schedules.chaos-mesh.org \
    stresschaos.chaos-mesh.org \
    timechaos.chaos-mesh.org \
    podchaos.chaos-mesh.org \
    workflows.chaos-mesh.org \
    workflownodes.chaos-mesh.org
    
echo "ChaosMesh is disabled"
