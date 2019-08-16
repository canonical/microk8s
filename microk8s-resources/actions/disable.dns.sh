#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling DNS"
echo "Reconfiguring kubelet"
KUBECTL="$SNAP/kubectl --kubeconfig=$SNAP/client.config"

# Delete the dns yaml
# We need to wait for the dns pods to terminate before we restart kubelet
echo "Removing DNS manifest"
pods_sys="$($KUBECTL get po -n kube-system 2>&1)"
if echo "$pods_sys" | grep "kube-dns" &> /dev/null 
then
  use_manifest dns delete
fi
if echo "$pods_sys" | grep "coredns" &> /dev/null
then
  use_manifest coredns delete
fi
sleep 15
dns=$(wait_for_service_shutdown "kube-system" "k8s-app=kube-dns")
if [[ $dns == fail ]]
then
  echo "DNS did not shut down on time. Proceeding."
fi

skip_opt_in_config "cluster-domain" kubelet
skip_opt_in_config "cluster-dns" kubelet
sudo systemctl restart snap.${SNAP_NAME}.daemon-kubelet
kubelet=$(wait_for_service kubelet)
if [[ $kubelet == fail ]]
then
  echo "Kubelet did not start on time. Proceeding."
fi
sleep 15
echo "DNS is disabled"
