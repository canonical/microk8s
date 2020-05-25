#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Dashboard"

ARCH=$(arch)
TAG="0.25.1"
EXTRA_ARGS="- --publish-status-address=127.0.0.1"


KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
# Clean up old ingress controller resources in the default namespace, in case these are still lurking around.  
$KUBECTL delete service -n kube-system monitoring-grafana  > /dev/null 2>&1 || true
$KUBECTL delete service -n kube-system monitoring-influxdb  > /dev/null 2>&1 || true
$KUBECTL delete service -n kube-system heapster  > /dev/null 2>&1 || true

$KUBECTL delete deployment -n kube-system monitoring-influxdb-grafana-v4  > /dev/null 2>&1 || true
$KUBECTL delete deployment -n kube-system heapster-v1.5.2  > /dev/null 2>&1 || true
$KUBECTL delete clusterrolebinding heapster  > /dev/null 2>&1 || true
$KUBECTL delete configmap -n kube-system heapster-config  > /dev/null 2>&1 || true
$KUBECTL delete configmap -n kube-system eventer-config  > /dev/null 2>&1 || true
$KUBECTL delete serviceaccount -n kube-system heapster  > /dev/null 2>&1 || true 

use_manifest dashboard delete 

echo "Dashboard is disabled"
