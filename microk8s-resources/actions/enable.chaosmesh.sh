#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh
VERSION="2.0.5"
NAMESPACE="chaos-testing"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

"$SNAP/microk8s-enable.wrapper" dns
"$SNAP/microk8s-enable.wrapper" helm3

echo ""
echo "Enabling ChaosMesh"

VALUES=""

for i in "$@"
do
case $i in
    --version=*)
    VERSION="${i#*=}"
    shift # past argument=value
    ;;
    -f=*|--values=*)
    VALUES="${i#*=}"
    shift # past argument=value
    ;;
    *)
          # unknown option
    ;;
esac
done
if [ -n "$VALUES" ]; then
    echo "Overrides file: $VALUES"
fi


# make sure the "chaos-testing"  namespaces exists
$KUBECTL create namespace "$NAMESPACE" > /dev/null 2>&1 || true

HELM="$SNAP_DATA/bin/helm3 --kubeconfig=$SNAP_DATA/credentials/client.config"

$HELM repo add chaos-mesh https://charts.chaos-mesh.org

if [ -z "$VALUES" ]
then
    $HELM upgrade chaos-mesh --install chaos-mesh/chaos-mesh \
        --namespace chaos-testing  \
        --set chaosDaemon.runtime=containerd \
        --set chaosDaemon.socketPath=/var/snap/microk8s/common/run/containerd.sock \
        --version $VERSION
else
    $HELM upgrade chaos-mesh --install chaos-mesh/chaos-mesh \
        --namespace chaos-testing  \
        --set chaosDaemon.runtime=containerd \
        --set chaosDaemon.socketPath=/var/snap/microk8s/common/run/containerd.sock \
        --version $VERSION \
        -f "$VALUES"
fi

# print a final help message
echo "ChaosMesh has been installed"
