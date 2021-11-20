#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh
CA_CERT=/snap/core18/current/etc/ssl/certs/ca-certificates.crt

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

do_prerequisites() {
  # enable dns service
  "$SNAP/microk8s-enable.wrapper" dns
  ${SNAP}/microk8s-status.wrapper --wait-ready --timeout 30 >/dev/null
  run_with_sudo mkdir -p "${SNAP_DATA}/keda"
}


get_keda () {
  KEDA_VERSION="v2.4.0"
  KEDA_ERSION=$(echo $KEDA_VERSION | sed 's/v//g')
  echo "Fetching keda version $KEDA_ERSION."
  run_with_sudo "${SNAP}/usr/bin/curl" --cacert $CA_CERT -L https://github.com/kedacore/keda/releases/download/${KEDA_VERSION}/keda-${KEDA_ERSION}.yaml -o "$SNAP_DATA/keda/keda.yaml"
}


enable_keda() {
  echo "Enabling KEDA"
  $KUBECTL apply -f "${SNAP_DATA}/keda/keda.yaml" 
}

do_prerequisites
get_keda
enable_keda

echo "The KEDA is enabled."
