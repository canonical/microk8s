#!/usr/bin/env bash

set -eux

source $SNAP/actions/common/utils.sh

function disable_kubeflow() {
  echo "Disabling Kubeflow..."
  if "$SNAP/microk8s-juju.wrapper" show-controller uk8s >/dev/null 2>&1; then
    "$SNAP/microk8s-juju.wrapper" destroy-controller -y uk8s --destroy-all-models --destroy-storage
    "$SNAP/microk8s-disable.wrapper" juju
    echo "Kubeflow is now disabled."
  else
    echo "Kubeflow has already been disabled."
  fi
}

disable_kubeflow

