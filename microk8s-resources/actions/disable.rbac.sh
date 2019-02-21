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
fi

echo "Removing default RBAC resources"
tmp_manifest="${SNAP_USER_DATA}/tmp/temp.rbac.yaml"
mkdir -p "${SNAP_USER_DATA}/tmp"
touch "${tmp_manifest}"
for type in rolebindings roles clusterrolebindings clusterroles; do
    echo -e "---\n" >> "${tmp_manifest}"
    "$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" get ${type} --all-namespaces -o yaml >> "${tmp_manifest}"
done
"$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" delete -f "${tmp_manifest}"
rm "${tmp_manifest}"

echo "RBAC is disabled"
