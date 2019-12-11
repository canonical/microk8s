#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Hubble"

"$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" delete -f "$SNAP_DATA/actions/hubble.yaml"

# Give K8s some time to process the deletion request
hubble=$(wait_for_service_shutdown "kube-system" "k8s-app=hubble")
if [[ $hubble == fail ]]
then
  echo "Hubble did not shut down on time. Proceeding."
fi

run_with_sudo rm -rf $SNAP_DATA/actions/hubble*.yaml

echo "Hubble is terminating"
