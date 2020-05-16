#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Metrics-Server"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
# Clean up old metrics-server  
use_manifest metrics-server-deprecated delete
use_manifest metrics-server delete 

skip_opt_in_config "authentication-token-webhook" kubelet
skip_opt_in_config "authorization-mode" kubelet

restart_service kubelet
kubelet=$(wait_for_service kubelet)
if [[ $kubelet == fail ]]
then
  echo "Kubelet did not start on time. Proceeding."
fi
sleep 15

echo " Metrics-Server is disabled"
