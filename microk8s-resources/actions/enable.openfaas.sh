#!/usr/bin/env bash

set -ex

source $SNAP/actions/common/utils.sh

OF_NAMESPACE="openfaas"
FN_NAMESPACE="openfaas-fn"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

"$SNAP/microk8s-enable.wrapper" dns
"$SNAP/microk8s-enable.wrapper" helm3

echo ""
echo "Enabling OpenFaaS"

OPERATOR=false
AUTH=true
VALUES=""

for i in "$@"
do
case $i in
    --operator)
    OPERATOR=true
    shift # past argument
    ;;
    --no-auth)
    AUTH=false
    shift # past argument
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

echo "Operator: $OPERATOR"
echo "Basic Auth enabled: $AUTH"
if [ -n "$VALUES" ]; then
    echo "Overrides file: $VALUES"
fi


# make sure the "openfaas" and "openfaas-fn" namespaces exists
$KUBECTL create namespace "$OF_NAMESPACE" > /dev/null 2>&1 || true
$KUBECTL create namespace "$FN_NAMESPACE" > /dev/null 2>&1 || true

HELM="$SNAP_DATA/bin/helm3 --kubeconfig=$SNAP_DATA/credentials/client.config"

$HELM repo add openfaas https://openfaas.github.io/faas-netes/

if [ -z "$VALUES" ]
then
    $HELM upgrade openfaas --install openfaas/openfaas \
        --namespace openfaas  \
        --set functionNamespace=openfaas-fn \
        --set createCRDs=true \
        --set operator.create=$OPERATOR \
        --set basic_auth=$AUTH \
        --set generateBasicAuth=$AUTH
else
    $HELM upgrade openfaas --install openfaas/openfaas \
        --namespace openfaas  \
        --set functionNamespace=openfaas-fn \
        --set createCRDs=true \
        --set operator.create=$OPERATOR \
        --set basic_auth=$AUTH \
        --set generateBasicAuth=$AUTH \
        -f "$VALUES"
fi

# print a final help message
echo "OpenFaaS has been installed"
