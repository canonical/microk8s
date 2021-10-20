#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh
HELM="$SNAP_DATA/bin/helm3 --kubeconfig=$SNAP_DATA/credentials/client.config"
KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
OPENEBS_NS="openebs"

echo "Disabling OpenEBS"

forceful_bdc_delete() {
    
    MESSAGE="Deleting BDC forcefully"
    
    if [[ $1 == "spc" ]]
    then
      EXTRA_LABELS="-l openebs.io/storage-pool-claim"
      MESSAGE="Deleting BDCs from SPCs forcefully"
    elif [[ $1 == "cspc" ]]
    then
      EXTRA_LABELS="-l openebs.io/cstor-pool-cluster"
      MESSAGE="Deleting BDCs from CSPCs forcefully"
    fi

    echo $MESSAGE
    OBJ_LIST=`$KUBECTL -n $OPENEBS_NS get blockdeviceclaims.openebs.io $EXTRA_LABELS -o=jsonpath='{.items[*].metadata.name}'` || true
    
    if [ -n "$OBJ_LIST" ]
    then
      $KUBECTL -n $OPENEBS_NS patch blockdeviceclaims.openebs.io ${OBJ_LIST} --type=json -p='[{"op":"remove", "path":"/metadata/finalizers"}]' || true
      $KUBECTL -n $OPENEBS_NS delete blockdeviceclaims.openebs.io ${OBJ_LIST} --timeout=60s --ignore-not-found || true
    fi
}

bd_remove_finalizer() {
    
    #OBJ_LIST=`$KUBECTL -n $OPENEBS_NS get blockdevice.openebs.io -o=jsonpath='{.items[?(@.status.claimState=="Claimed")].metadata.name}'`
    #$KUBECTL -n $OPENEBS_NS patch blockdevice.openebs.io ${OBJ_LIST} --type=json -p='[{"op":"replace", "path":"/status/claimState", "value":"Released"}]' || true

    #echo "Waiting for BlockDevice cleanup... (30 seconds)"
    #sleep 30

    OBJ_LIST=`$KUBECTL -n $OPENEBS_NS get blockdevice.openebs.io -o=jsonpath='{.items[?(@.status.claimState!="Unclaimed")].metadata.name}'` || true
    $KUBECTL -n $OPENEBS_NS patch blockdevice.openebs.io ${OBJ_LIST} --type=json -p='[{"op":"remove", "path":"/metadata/finalizers"}]' || true
}

disable_legacy() {

    echo "Deleting validatingwebhookconfiguration"
    $KUBECTL delete validatingwebhookconfiguration openebs-validation-webhook-cfg --ignore-not-found || true
    
    forceful_bdc_delete "spc"

    $KUBECTL delete storageclass openebs-jiva-default \
        openebs-snapshot-promoter \
        --timeout=60s --ignore-not-found || true
}

disable_cstor() {

    echo "Deleting OpenEBS cStor resources"
    $KUBECTL -n $OPENEBS_NS delete --all cstorpoolclusters.cstor.openebs.io --timeout=60s || CSPC_DEL_FAILED=$?
    
    if [ -n "$CSPC_DEL_FAILED" ]
    then
      echo "Deleting OpenEBS cStor validatingwebhookconfiguration"
      $KUBECTL delete validatingwebhookconfiguration openebs-cstor-validation-webhook --timeout=60s --ignore-not-found || true
	
      # Resources with Finalizers
      # cvr, cvc, cspi, cspc, cva
      OBJ_LIST="cstorvolumereplicas.cstor.openebs.io,cstorvolumeconfigs.cstor.openebs.io,cstorpoolinstances.cstor.openebs.io,cstorpoolclusters.cstor.openebs.io,cstorvolumeattachments.cstor.openebs.io"
      OBJ_LIST_FOUND=`$KUBECTL -n $OPENEBS_NS get $OBJ_LIST -o name` || true
      $KUBECTL -n $OPENEBS_NS patch $OBJ_LIST_FOUND --type=json -p='[{"op":"remove", "path":"/metadata/finalizers"}]' || true
        
        
      # Resources without Finalizers
      # cbackup, ccompletedbackup, crestore, cvp, cv
      # [Now patched] cvr, cvc, cspi, cspc, cva
      OBJ_LIST="cstorvolumereplicas.cstor.openebs.io,cstorvolumeconfigs.cstor.openebs.io,cstorpoolinstances.cstor.openebs.io,cstorpoolclusters.cstor.openebs.io,cstorbackups.cstor.openebs.io,cstorcompletedbackups.cstor.openebs.io,cstorrestores.cstor.openebs.io,cstorvolumeattachments.cstor.openebs.io,cstorvolumepolicies.cstor.openebs.io,cstorvolumes.cstor.openebs.io"
      OBJ_LIST_FOUND=`$KUBECTL -n $OPENEBS_NS get $OBJ_LIST -o name` || true
      $KUBECTL -n $OPENEBS_NS delete $OBJ_LIST_FOUND --timeout=60s --ignore-not-found || true

      forceful_bdc_delete "cspc"
      # Forceful cleanup does not wait for BlockDevice cleanup
    else
      echo "Waiting for BlockDevice cleanup... (30 seconds)"
      sleep 30
    fi
}

disable_openebs() {

    # LEGACY
    disable_legacy

    # CSTOR-CSI
    disable_cstor

    # BLOCKDEVICES and BLOCKDEVICECLAIMS
    BD_WITH_FINALIZER=`$KUBECTL -n $OPENEBS_NS get blockdevice.openebs.io -o=jsonpath='{.items[?(@.status.claimState!="Unclaimed")].metadata.name}'` || true
    if [ -n "$BD_WITH_FINALIZER" ]
    then
      forceful_bdc_delete
      bd_remove_finalizer
    fi
   
    # Helm chart
    $HELM uninstall openebs -n $OPENEBS_NS || true
    
    # Default StorageClasses
    $KUBECTL delete storageclass openebs-hostpath \
        openebs-device \
        openebs-jiva-csi-default \
        --timeout=60s --ignore-not-found|| true

    KUBECTL_DELETE_ARGS="--wait=true --timeout=180s --ignore-not-found=true"
    $KUBECTL delete $KUBECTL_DELETE_ARGS namespace $OPENEBS_NS || true

    # CRDs
    $KUBECTL delete customresourcedefinition blockdeviceclaims.openebs.io \
        blockdevices.openebs.io \
        cstorbackups.cstor.openebs.io \
        cstorcompletedbackups.cstor.openebs.io \
        cstorpoolclusters.cstor.openebs.io \
        cstorpoolinstances.cstor.openebs.io \
        cstorrestores.cstor.openebs.io \
        cstorvolumeattachments.cstor.openebs.io \
        cstorvolumeconfigs.cstor.openebs.io \
        cstorvolumepolicies.cstor.openebs.io \
        cstorvolumereplicas.cstor.openebs.io \
        cstorvolumes.cstor.openebs.io \
        jivavolumepolicies.openebs.io \
        jivavolumes.openebs.io \
        migrationtasks.openebs.io \
        upgradetasks.openebs.io \
        --timeout=60s --ignore-not-found || true

    echo "OpenEBS disabled"
    echo "Manually clean up the directory $SNAP_COMMON/var/openebs/"
}


disable_openebs
