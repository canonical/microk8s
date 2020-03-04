#!/usr/bin/env bash

set -ex
source $SNAP/actions/common/utils.sh
echo "Disabling Jaeger"
read -ra ARGUMENTS <<< "$1"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

if [ ! -z "${ARGUMENTS[@]}" ]
then

  $KUBECTL delete -f "${SNAP}/actions/jaeger/crds"
  yaml_path=${SNAP}/actions/jaeger/
  manifests="service_account.yaml role.yaml role_binding.yaml operator.yaml"
  KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config -n ${ARGUMENTS[0]}"
  for yaml in $manifests
  do
    sed "s/namespace: default/namespace: ${ARGUMENTS[0]}/g" $yaml_path/$yaml | $KUBECTL delete -f -
    sleep 3
  done

else

  $KUBECTL delete -f "${SNAP}/actions/jaeger"
  $KUBECTL delete -f "${SNAP}/actions/jaeger/crds"

fi
echo "The Jaeger operator is disabled"
