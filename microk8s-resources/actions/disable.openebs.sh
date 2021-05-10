#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh
HELM="$SNAP_DATA/bin/helm3 --kubeconfig=$SNAP_DATA/credentials/client.config"
KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

echo "Disabling OpenEBS"

read -ra ARGUMENTS <<< "$1"

disable_openebs() {

    echo "Deleting OpenEBS SPC in case of cStor"
    $KUBECTL -n openebs delete --all spc --timeout=60s || true

    echo "Deleting OpenEBS BlockDevicePool"
    $KUBECTL -n openebs delete --all bdc --timeout=60s || true

    echo "Deleting OpenEBS cStor custom resources"
    $KUBECTL -n openebs delete --all cvr --timeout=60s || true
    $KUBECTL -n openebs delete --all cstorvolume  --timeout=60s || true

    OPENEBS_SCS=$(kubectl get storageclasses -o=name | awk -F/ '{if ($2 ~ /^(openebs-.*)$/) print}' | paste -s --delimiters=' ')
    if [ -n "$OPENEBS_SCS" ]
    then
      echo "Deleting OpenEBS storage classes $OPENEBS_SCS"
      $KUBECTL delete $OPENEBS_SCS --timeout=60s
    fi

    echo "Deleting OpenEBS block devices"
    $KUBECTL -n openebs delete --all bd  --timeout=60s || true

    $HELM uninstall -n openebs openebs
    $KUBECTL delete validatingwebhookconfigurations  openebs-validation-webhook-cfg || true
    $KUBECTL delete crd castemplates.openebs.io || true
    $KUBECTL delete crd cstorpools.openebs.io || true
    $KUBECTL delete crd cstorpoolinstances.openebs.io || true
    $KUBECTL delete crd cstorvolumeclaims.openebs.io || true
    $KUBECTL delete crd cstorvolumereplicas.openebs.io || true
    $KUBECTL delete crd cstorvolumepolicies.openebs.io || true
    $KUBECTL delete crd cstorvolumes.openebs.io || true
    $KUBECTL delete crd runtasks.openebs.io || true
    $KUBECTL delete crd storagepoolclaims.openebs.io || true
    $KUBECTL delete crd storagepools.openebs.io || true
    $KUBECTL delete crd volumesnapshotdatas.volumesnapshot.external-storage.k8s.io || true
    $KUBECTL delete crd volumesnapshots.volumesnapshot.external-storage.k8s.io || true
    $KUBECTL delete crd blockdevices.openebs.io || true
    $KUBECTL delete crd blockdeviceclaims.openebs.io || true
    $KUBECTL delete crd cstorbackups.openebs.io || true
    $KUBECTL delete crd cstorrestores.openebs.io || true
    $KUBECTL delete crd cstorcompletedbackups.openebs.io || true
    $KUBECTL delete crd upgradetasks.openebs.io || true
    $KUBECTL delete crd cstorpoolclusters.cstor.openebs.io || true
    $KUBECTL delete crd cstorpoolinstances.cstor.openebs.io || true
    $KUBECTL delete crd cstorvolumeattachments.cstor.openebs.io || true
    $KUBECTL delete crd cstorvolumeconfigs.cstor.openebs.io || true
    $KUBECTL delete crd cstorvolumepolicies.cstor.openebs.io || true
    $KUBECTL delete crd cstorvolumereplicas.cstor.openebs.io || true
    $KUBECTL delete crd cstorvolumes.cstor.openebs.io || true

    KUBECTL_DELETE_ARGS="--wait=true --timeout=180s --ignore-not-found=true"
    $KUBECTL delete $KUBECTL_DELETE_ARGS namespace openebs || true

    echo "OpenEBS disabled"
    echo "Manually clean up the directory $SNAP_COMMON/var/openebs/"
}


if [ ! -z "${ARGUMENTS[@]}" ] && [ "${ARGUMENTS[@]}" = "force" ]
then
  disable_openebs
else
  echo "Information with regards to OpenEBS uninstallation (https://docs.openebs.io/docs/next/uninstall.html)".
  read -p "Have you deleted all the pods and PersistentVolumeClaims using OpenEBS PVC? (Y/N): " confirm && [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]] || exit 1
  disable_openebs
fi