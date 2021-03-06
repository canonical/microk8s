#!/usr/bin/env bash

set -eu

source "$SNAP/actions/common/utils.sh"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

OPENEBS_NS="openebs"
"$SNAP/microk8s-enable.wrapper" dns
"$SNAP/microk8s-enable.wrapper" helm3


#Check if iscsid is installed 

if systemctl is-enabled iscsid | grep enabled &> /dev/null
  then
    printf -- 'iscsid is not available'
    printf -- 'Please refer to the OpenEBS prerequisites (https://docs.openebs.io/docs/next/prerequisites.html)'
    exit   
fi

# make sure the "openebs" namespace exist
$KUBECTL create namespace "$OPENEBS_NS" > /dev/null 2>&1 || true

HELM="$SNAP_DATA/bin/helm3 --kubeconfig=$SNAP_DATA/credentials/client.config"

$HELM repo add openebs https://openebs.github.io/charts
$HELM repo repo update
$HELM repo -n openebs install openebs openebs/openebs \
    --set varDirectoryPath.baseDir="$SNAP_COMMON/var/openebs/" \
    --set jiva.defaultStoragePath="$SNAP_COMMON/var/openebs/"

echo "OpenEBS is installed"

echo "****************************************************************************************************"
echo "When using OpenEBS on a single node setup, it is recommended to use the openebs-hostpath StorageClass"
echo "Create the local hostpath PersistentVolumeClaim "
echo "" 
echo "kind: PersistentVolumeClaim 
apiVersion: v1
metadata:
  name: local-hostpath-pvc
spec:
  storageClassName: openebs-hostpath
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5G
"

echo "If you plan to use OpenEBS on multi nodes, you can use the openebs-jiva-default StorageClass."

echo "kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: demo-volume-claim
spec:
  storageClassName: openebs-jiva-default
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5G
"

echo "****************************************************************************************************"