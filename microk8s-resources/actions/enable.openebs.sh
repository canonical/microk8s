#!/usr/bin/env bash

set -eu

source "$SNAP/actions/common/utils.sh"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

OPENEBS_NS="openebs"

# Check if iscsid is installed 
if ! systemctl is-enabled iscsid | grep enabled &> /dev/null
  then
    echo "iscsid is not available or enabled.  Make sure iscsi is installed on all nodes."
    echo "To enable iscsid: "
    echo "      sudo systemctl enable iscsid"
    echo "Please refer to the OpenEBS prerequisites (https://docs.openebs.io/docs/next/prerequisites.html)"
    exit   
fi

"$SNAP/microk8s-enable.wrapper" dns
"$SNAP/microk8s-enable.wrapper" helm3


# make sure the "openebs" namespace exist
$KUBECTL create namespace "$OPENEBS_NS" > /dev/null 2>&1 || true

HELM="$SNAP_DATA/bin/helm3 --kubeconfig=$SNAP_DATA/credentials/client.config"

$HELM repo add openebs https://openebs.github.io/charts
$HELM repo update
$HELM -n openebs install openebs openebs/openebs \
    --set varDirectoryPath.baseDir="$SNAP_COMMON/var/openebs" \
    --set jiva.defaultStoragePath="$SNAP_COMMON/var/openebs" \
    --set localprovisioner.basePath="$SNAP_COMMON/var/openebs/local" \
    --set ndm.sparse.path="$SNAP_COMMON/var/openebs/sparse"

echo "OpenEBS is installed"

# Help sections
echo "" 
echo "" 
echo "-----------------------"
echo "" 
echo "When using OpenEBS with a single node MicroK8s, it is recommended to use the openebs-hostpath StorageClass"
echo "An example of creating a PersistentVolumeClaim utilizing the openebs-hostpath StorageClass"
echo "" 
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
echo "" 
echo "" 
echo "-----------------------"
echo "" 
echo "If you are planning to use OpenEBS with multi nodes, you can use the openebs-jiva-default StorageClass."
echo "An example of creating a PersistentVolumeClaim utilizing the openebs-jiva-default StorageClass"
echo "" 
echo "" 
echo "kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: jiva-volume-claim
spec:
  storageClassName: openebs-jiva-default
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5G
"
