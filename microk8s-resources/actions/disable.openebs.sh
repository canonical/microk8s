#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling OpenEBS"

read -ra ARGUMENTS <<< "$1"

declare -A map
map[\$SNAP_COMMON]="$SNAP_COMMON"

HELM="$SNAP_DATA/bin/helm3 --kubeconfig=$SNAP_DATA/credentials/client.config"
$HELM uninstall -n openebs openebs

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

$KUBECTL delete validatingwebhookconfigurations  openebs-validation-webhook-cfg
$KUBECTL delete crd castemplates.openebs.io
$KUBECTL delete crd cstorpools.openebs.io
$KUBECTL delete crd cstorpoolinstances.openebs.io
$KUBECTL delete crd cstorvolumeclaims.openebs.io
$KUBECTL delete crd cstorvolumereplicas.openebs.io
$KUBECTL delete crd cstorvolumepolicies.openebs.io
$KUBECTL delete crd cstorvolumes.openebs.io
$KUBECTL delete crd runtasks.openebs.io
$KUBECTL delete crd storagepoolclaims.openebs.io
$KUBECTL delete crd storagepools.openebs.io
$KUBECTL delete crd volumesnapshotdatas.volumesnapshot.external-storage.k8s.io
$KUBECTL delete crd volumesnapshots.volumesnapshot.external-storage.k8s.io
$KUBECTL delete crd blockdevices.openebs.io
$KUBECTL delete crd blockdeviceclaims.openebs.io
$KUBECTL delete crd cstorbackups.openebs.io
$KUBECTL delete crd cstorrestores.openebs.io
$KUBECTL delete crd cstorcompletedbackups.openebs.io
$KUBECTL delete crd upgradetasks.openebs.io
$KUBECTL delete crd cstorpoolclusters.cstor.openebs.io
$KUBECTL delete crd cstorpoolinstances.cstor.openebs.io
$KUBECTL delete crd cstorvolumeattachments.cstor.openebs.io
$KUBECTL delete crd cstorvolumeconfigs.cstor.openebs.io
$KUBECTL delete crd cstorvolumepolicies.cstor.openebs.io
$KUBECTL delete crd cstorvolumereplicas.cstor.openebs.io
$KUBECTL delete crd cstorvolumes.cstor.openebs.io

KUBECTL_DELETE_ARGS="--wait=true --timeout=180s --ignore-not-found=true"
$KUBECTL delete $KUBECTL_DELETE_ARGS namespace openebs > /dev/null 2>&1 || true

echo "OpenEBS disabled"
echo "Manually clean up the directory $SNAP_COMMON/var/openebs/"