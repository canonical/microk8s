#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh


echo "Disabling RBAC"

echo "Reconfiguring apiserver"
refresh_opt_in_config "authorization-mode" "AlwaysAllow" kube-apiserver
sudo systemctl restart snap.${SNAP_NAME}.daemon-apiserver
apiserver=$(wait_for_service apiserver)
if [[ $apiserver == fail ]]
then
  echo "apiserver did not start on time. Proceeding."
  sleep 15
else
  # Seems to need to wait a bit anyway
  sleep 5
fi

echo "Removing default RBAC resources"
KUBECTL="$SNAP/kubectl --kubeconfig=$SNAP/client.config"
tmp_manifest="${SNAP_USER_DATA}/tmp/temp.rbac.yaml"
trap "rm -f '${tmp_manifest}'" EXIT ERR INT TERM
mkdir -p "${SNAP_USER_DATA}/tmp"
touch "${tmp_manifest}"
for type in rolebindings roles clusterrolebindings clusterroles; do
  echo -e "---\n" >> "${tmp_manifest}"
  $KUBECTL get ${type} --all-namespaces --selector kubernetes.io/bootstrapping=rbac-defaults -o yaml >> "${tmp_manifest}"
done
$KUBECTL delete -f "${tmp_manifest}"

echo "RBAC is disabled"
