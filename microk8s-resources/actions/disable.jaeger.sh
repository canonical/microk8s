#!/usr/bin/env bash

set -e
source $SNAP/actions/common/utils.sh
echo "Disabling Jaeger"
read -ra ARGUMENTS <<< "$1"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

if [ ! -z "${ARGUMENTS[@]}" ]
then

  $KUBECTL delete -f "${SNAP}/actions/jaeger/crds"

  yaml_path=${SNAP}/actions/jaeger/

  sed "s/namespace: default/namespace: ${ARGUMENTS[0]}/g" $yaml_path/service_account.yaml | $KUBECTL delete -n ${ARGUMENTS[0]} -f -
  sleep 3
  sed "s/namespace: default/namespace: ${ARGUMENTS[0]}/g" $yaml_path/role.yaml | $KUBECTL delete -n ${ARGUMENTS[0]} -f -
  sleep 3
  sed "s/namespace: default/namespace: ${ARGUMENTS[0]}/g" $yaml_path/role_binding.yaml | $KUBECTL delete -n ${ARGUMENTS[0]} -f -
  sleep 3
  KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config -n ${ARGUMENTS[0]}"
  sed "s/namespace: default/namespace: ${ARGUMENTS[0]}/g" $yaml_path/operator.yaml | $KUBECTL delete -n ${ARGUMENTS[0]} -f -

else

  $KUBECTL delete -f "${SNAP}/actions/jaeger"
  $KUBECTL delete -f "${SNAP}/actions/jaeger/crds"

fi
echo "The Jaeger operator is disabled"
