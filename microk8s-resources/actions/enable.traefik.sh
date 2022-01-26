#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

"$SNAP/microk8s-enable.wrapper" dns
"$SNAP/microk8s-enable.wrapper" helm3
"$SNAP/microk8s-enable.wrapper" hostpath-storage

NAMESPACE_PTR="traefik"
KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

echo "Enabling traefik ingress controller"

# make sure the "traefik" namespace exists
$KUBECTL create namespace "$NAMESPACE_PTR" > /dev/null 2>&1 || true
# load the CRD and wait for it to be installed
#$KUBECTL apply -f "${SNAP}/actions/traefik.yaml"
VALUES="$@"

for i in "$@"
do
case $i in
    -f=*|--values=*)
    VALUES="${i#*=}"
    shift # past argument=value
    ;;
    *)
          # unknown option
    ;;
esac
done


HELM="$SNAP_DATA/bin/helm3 --kubeconfig=$SNAP_DATA/credentials/client.config"

$HELM repo add traefik https://helm.traefik.io/traefik
$HELM repo update
if [ -z "$VALUES" ]
then
  $HELM upgrade --install traefik  traefik/traefik -n $NAMESPACE_PTR
else
  $HELM upgrade --install traefik -f "$2" traefik/traefik -n $NAMESPACE_PTR
fi

# print a final help message
echo "Traefik has been installed via helm. For enabling dashboard pl use port forwarding or access through node port"
