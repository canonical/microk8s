#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh
HELM="$SNAP_DATA/bin/helm3 --kubeconfig=$SNAP_DATA/credentials/client.config"
KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
OPENEBS_NS="openebs"

echo "Disabling OpenEBS"

read -ra ARGUMENTS <<< "$1"

forceful_bdc_delete() {
    
    if [ $1 = "spc" ]
    then
      EXTRA_LABELS="-l openebs.io/storage-pool-claim"
    fi

    echo "Deleting BDC forcefully"
    OBJ_LIST=`$KUBECTL -n $OPENEBS_NS get blockdeviceclaims.openebs.io $EXTRA_LABELS -o=jsonpath='{.items[*].metadata.name}'` || true
    $KUBECTL -n $OPENEBS_NS patch blockdeviceclaims.openebs.io ${OBJ_LIST} --type=json -p='[{"op":"remove", "path":"/metadata/finalizers"}]' || true
    $KUBECTL -n $OPENEBS_NS delete blockdeviceclaims.openebs.io ${OBJ_LIST} --timeout=60s || true
}

forceful_spc_delete() {

    #echo "Deleting validatingwebhookconfiguration"
    #$KUBECTL delete validatingwebhookconfiguration openebs-validation-webhook-cfg || true

    echo "Deleting CStorVolumeReplica forcefully"
    OBJ_LIST=`$KUBECTL -n $OPENEBS_NS get cstorvolumereplicas.openebs.io -o=jsonpath='{.items[*].metadata.name}'` || true
    $KUBECTL -n $OPENEBS_NS patch cstorvolumereplicas.openebs.io ${OBJ_LIST} --type=json -p='[{"op":"remove", "path":"/metadata/finalizers"}]' || true
    $KUBECTL -n $OPENEBS_NS delete --all cstorvolumereplicas.openebs.io --timeout=60s || true

    echo "Deleting CStorVolume forcefully"
    $KUBECTL -n $OPENEBS_NS delete --all cstorvolumes.openebs.io --timeout=60s || true

    echo "Deleting CSP forcefully"
    OBJ_LIST=`$KUBECTL get cstorpools.openebs.io -o=jsonpath='{.items[*].metadata.name}'` || true
    $KUBECTL patch cstorpools.openebs.io ${OBJ_LIST} --type=json -p='[{"op":"remove", "path":"/metadata/finalizers"}]' || true
    $KUBECTL delete --all cstorpools.openebs.io --timeout=60s || true

    forceful_bdc_delete "spc"

    echo "Deleting SPC forcefully"
    OBJ_LIST=`$KUBECTL get storagepoolclaims.openebs.io -o=jsonpath='{.items[*].metadata.name}'` || true
    $KUBECTL patch storagepoolclaims.openebs.io ${OBJ_LIST} --type=json -p='[{"op":"remove", "path":"/metadata/finalizers"}]' || true
    $KUBECTL delete --all storagepoolclaims.openebs.io --timeout=60s || true
}

bd_remove_finalizer() {
    
    #OBJ_LIST=`$KUBECTL -n $OPENEBS_NS get blockdevice.openebs.io -o=jsonpath='{.items[?(@.status.claimState=="Claimed")].metadata.name}'`
    #$KUBECTL -n $OPENEBS_NS patch blockdevice.openebs.io ${OBJ_LIST} --type=json -p='[{"op":"replace", "path":"/status/claimState", "value":"Released"}]' || true

    #echo "Waiting for BlockDevice cleanup... (20 seconds)"
    #sleep 20

    OBJ_LIST=`$KUBECTL -n $OPENEBS_NS get blockdevice.openebs.io -o=jsonpath='{.items[?(@.status.claimState!="Unclaimed")].metadata.name}'` || true
    $KUBECTL -n $OPENEBS_NS patch blockdevice.openebs.io ${OBJ_LIST} --type=json -p='[{"op":"remove", "path":"/metadata/finalizers"}]' || true
}

disable_openebs() {

    $HELM uninstall -n $OPENEBS_NS openebs || true

    echo "Deleting OpenEBS SPCs in case of cStor"
    $KUBECTL delete --all storagepoolclaims.openebs.io --timeout=60s || SPC_DEL_FAILED=$?

    if [ -n "$SPC_DEL_FAILED" ]
    then
      forceful_spc_delete
    fi

    echo "Deleting OpenEBS StoragePools in case of Jiva"
    $KUBECTL delete --all storagepool.openebs.io --timeout=60s || true

    BD_WITH_FINALIZER=`$KUBECTL -n $OPENEBS_NS get blockdevice.openebs.io -o=jsonpath='{.items[?(@.status.claimState!="Unclaimed")].metadata.name}'` || true
    if [ -n "$BD_WITH_FINALIZER" ]
    then
      bd_remove_finalizer
    fi
    
    $KUBECTL delete customresourcedefinition castemplates.openebs.io \
cstorpools.openebs.io \
cstorpoolinstances.openebs.io \
cstorvolumeclaims.openebs.io \
cstorvolumereplicas.openebs.io \
cstorvolumepolicies.openebs.io \
cstorvolumes.openebs.io \
runtasks.openebs.io \
storagepoolclaims.openebs.io \
storagepools.openebs.io \
volumesnapshotdatas.volumesnapshot.external-storage.k8s.io \
volumesnapshots.volumesnapshot.external-storage.k8s.io \
blockdevices.openebs.io \
blockdeviceclaims.openebs.io \
cstorbackups.openebs.io \
cstorrestores.openebs.io \
cstorcompletedbackups.openebs.io \
upgradetasks.openebs.io \
--timeout=60s || true

    $KUBECTL delete storageclass openebs-hostpath \
openebs-device \
openebs-jiva-default \
openebs-snapshot-promoter \
--timeout=60s || true

    KUBECTL_DELETE_ARGS="--wait=true --timeout=180s --ignore-not-found=true"
    $KUBECTL delete $KUBECTL_DELETE_ARGS namespace $OPENEBS_NS --timeout=60s || true

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
