#!/usr/bin/env bash

set -eu

source $SNAP/actions/common/utils.sh

function disable_kubeflow() {
  echo "Disabling Kubeflow..."
  "$SNAP/microk8s-juju.wrapper" unregister -y uk8s || true
  "$SNAP/microk8s-kubectl.wrapper" delete ns controller-uk8s kubeflow || true
}

disable_kubeflow

