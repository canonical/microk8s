#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Jaeger"

"$SNAP/microk8s-enable.wrapper" dns ingress

read -ra ARGUMENTS <<< "$1"

if [ ! -z "${ARGUMENTS[@]}" ]
then

  KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config -n ${ARGUMENTS[0]}"
  $KUBECTL apply -f "${SNAP}/actions/jaeger/crds"

  yaml_path=${SNAP}/actions/jaeger/
  manifests="service_account.yaml role.yaml role_binding.yaml operator.yaml simplest.yaml"
  for yaml in $manifests
  do
    sed "s/namespace: default/namespace: ${ARGUMENTS[0]}/g" $yaml_path/$yaml | $KUBECTL apply -f -
    sleep 3
  done

else

  KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
  $KUBECTL apply -f "${SNAP}/actions/jaeger/crds"

  n=0
  until [ $n -ge 10 ]
  do
    sleep 3
    ($KUBECTL apply -f "${SNAP}/actions/jaeger/") && break
    n=$[$n+1]
    if [ $n -ge 10 ]; then
      echo "Jaeger operator failed to install"
      exit 1
    fi
  done

fi

echo "Jaeger is enabled"
