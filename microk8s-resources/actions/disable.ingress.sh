#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Ingress"

ARCH=$(arch)
TAG="v0.35.0"
DEFAULT_CERT="- ' '" # This default value is always fine when deleting resources.
DEFAULT_BACKEND_SERVICE="- ' '"
EXTRA_ARGS="- --publish-status-address=127.0.0.1"


KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
# Clean up old ingress controller resources in the default namespace, in case these are still lurking around.  
$KUBECTL delete deployment -n default default-http-backend > /dev/null 2>&1 || true
$KUBECTL delete service -n default default-http-backend > /dev/null 2>&1 || true
$KUBECTL delete serviceaccount -n default nginx-ingress-microk8s-serviceaccount > /dev/null 2>&1 || true 
$KUBECTL delete role -n default nginx-ingress-microk8s-role > /dev/null 2>&1 || true 
$KUBECTL delete rolebinding -n default nginx-ingress-microk8s > /dev/null 2>&1 || true 
$KUBECTL delete configmap -n default nginx-load-balancer-microk8s-conf > /dev/null 2>&1 || true
$KUBECTL delete daemonset -n default nginx-ingress-microk8s-controller > /dev/null 2>&1 || true


declare -A map
map[\$TAG]="$TAG"
map[\$DEFAULT_CERT]="$DEFAULT_CERT"
map[\$DEFAULT_BACKEND_SERVICE]="$DEFAULT_BACKEND_SERVICE"
map[\$EXTRA_ARGS]="$EXTRA_ARGS"
use_manifest ingress delete "$(declare -p map)"

echo "Ingress is disabled"
