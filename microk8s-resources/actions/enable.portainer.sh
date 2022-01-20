#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

NAMESPACE_PTR="portainer"

MANIFEST_PTR="https://raw.githubusercontent.com/portainer/k8s/master/deploy/manifests/portainer/portainer.yaml"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

<<<<<<< HEAD
microk8s enable hostpath-storage
microk8s enable dns
=======
"$SNAP/microk8s-enable.wrapper" hostpath-storage
"$SNAP/microk8s-enable.wrapper" dns
>>>>>>> upstream/master

echo "Enabling portainer"


# make sure the "portainer" namespace exists
$KUBECTL create namespace "$NAMESPACE_PTR" > /dev/null 2>&1 || true

# load the CRD and wait for it to be installed
$KUBECTL apply -f "$MANIFEST_PTR"
# change storage class that is default
#PVCNAME= "$KUBECTL get pvc -n "$NAMESPACE_PTR"  -o jsonpath="{.items[0].metadata.name}""
SC=$($KUBECTL get sc | grep default | awk  '{print $1}')
$KUBECTL patch pvc portainer -n  "$NAMESPACE_PTR"    -p '{ "spec": { "storageClassName": "'${SC}'"}}'


# print a final help message
echo "Portainer has been installed"
