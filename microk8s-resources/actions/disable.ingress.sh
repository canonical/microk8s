#!/usr/bin/env bash

set -ex

source $SNAP/actions/common/utils.sh

echo "Disabling Ingress"

ARCH=$(arch)
TAG="0.25.1"
EXTRA_ARGS="- --publish-status-address=127.0.0.1"


KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
# Clean up old ingress controller resources in the default namespace, in case these are still lurking around.  
$KUBECTL delete deployment -n default default-http-backend || true
$KUBECTL delete service -n default default-http-backend || true
$KUBECTL delete serviceaccount -n default nginx-ingress-microk8s-serviceaccount || true 
$KUBECTL delete role -n default nginx-ingress-microk8s-role || true 
$KUBECTL delete rolebinding -n default nginx-ingress-microk8s || true 
$KUBECTL delete configmap -n default nginx-load-balancer-microk8s-conf || true
$KUBECTL delete daemonset -n default nginx-ingress-microk8s-controller || true


declare -A map
map[\$TAG]="$TAG"
map[\$EXTRA_ARGS]="$EXTRA_ARGS"
use_manifest ingress delete "$(declare -p map)"

echo "Ingress is disabled"
