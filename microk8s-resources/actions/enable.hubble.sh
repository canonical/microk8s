#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh
CA_CERT=/snap/core/current/etc/ssl/certs/ca-certificates.crt
NAMESPACE=kube-system

"$SNAP/microk8s-enable.wrapper" cilium

echo "Enabling Hubble"

read -ra HUBBLE_VERSION <<< "$1"
if [ -z "$HUBBLE_VERSION" ]; then
  HUBBLE_VERSION="master"
fi
HUBBLE_ERSION=$(echo $HUBBLE_VERSION | sed 's/v//g')

if [ -f "$SNAP_DATA/actions/hubble-$HUBBLE_ERSION.yaml" ]
then
  echo "Hubble version $HUBBLE_VERSION is already installed."
else
  HUBBLE_DIR="hubble-$HUBBLE_ERSION"
  SOURCE_URI="https://github.com/cilium/hubble/archive"
  HUBBLE_LABELS="k8s-app=hubble"

  echo "Fetching hubble version $HUBBLE_VERSION."
  run_with_sudo mkdir -p "${SNAP_DATA}/tmp/hubble"
  (cd "${SNAP_DATA}/tmp/hubble"
  run_with_sudo "${SNAP}/usr/bin/curl" --cacert $CA_CERT -L $SOURCE_URI/$HUBBLE_VERSION.tar.gz -o "$SNAP_DATA/tmp/hubble/hubble.tar.gz"
  if ! run_with_sudo gzip -f -d "$SNAP_DATA/tmp/hubble/hubble.tar.gz"; then
    echo "Invalid version \"$HUBBLE_VERSION\". Must be a branch on https://github.com/cilium/hubble."
    exit 1
  fi
  run_with_sudo tar -xf "$SNAP_DATA/tmp/hubble/hubble.tar" "$HUBBLE_DIR/install" "$HUBBLE_DIR/$HUBBLE_CNI_CONF")

  # Generate the YAMLs for Csssss and apply them
  (cd "${SNAP_DATA}/tmp/hubble/$HUBBLE_DIR/install/kubernetes"
  ${SNAP_DATA}/bin/helm template hubble \
      --namespace $NAMESPACE \
      --set ui.enabled=true \
      --set listenClientUrls='{unix:///var/run/cilium/hubble.sock}' \
      --set server='unix:///var/run/cilium/hubble.sock' \
      | run_with_sudo tee hubble-$HUBBLE_ERSION.yaml >/dev/null)

  run_with_sudo cp "$SNAP_DATA/tmp/hubble/$HUBBLE_DIR/install/kubernetes/hubble-$HUBBLE_ERSION.yaml" "$SNAP_DATA/actions/hubble-$HUBBLE_ERSION.yaml"
  run_with_sudo ln -s "$SNAP_DATA/actions/hubble-$HUBBLE_ERSION.yaml" "$SNAP_DATA/actions/hubble.yaml"
  run_with_sudo sed -i 's;path: \(/var/run/cilium\);path: '"$SNAP_DATA"'\1;g' "$SNAP_DATA/actions/hubble.yaml"

  ${SNAP}/microk8s-status.wrapper --wait-ready >/dev/null
  echo "Deploying $SNAP_DATA/actions/hubble.yaml. This may take several minutes."
  "$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" apply -f "$SNAP_DATA/actions/hubble.yaml"
  "$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" -n $NAMESPACE rollout status ds/hubble

  run_with_sudo rm -rf "$SNAP_DATA/tmp/hubble"
fi

HUBBLE_UI=$("$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" -n "$NAMESPACE" get pod -l "k8s-app=hubble-ui" -o jsonpath='{.items[0].status.podIP}')
echo "Hubble is enabled with UI on http://$HUBBLE_UI:12000"
