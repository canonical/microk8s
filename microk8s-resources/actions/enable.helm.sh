#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh
CA_CERT=/snap/core/current/etc/ssl/certs/ca-certificates.crt

echo "Enabling Helm"

if [ ! -f "${SNAP_DATA}/bin/helm" ]
then
  SOURCE_URI="https://get.helm.sh"
  HELM_VERSION="v2.16.7"

  echo "Fetching helm version $HELM_VERSION."
  run_with_sudo mkdir -p "${SNAP_DATA}/tmp/helm"
  (cd "${SNAP_DATA}/tmp/helm"
  run_with_sudo "${SNAP}/usr/bin/curl" --cacert $CA_CERT -L $SOURCE_URI/helm-$HELM_VERSION-linux-$(arch).tar.gz -o "$SNAP_DATA/tmp/helm/helm.tar.gz"
  run_with_sudo gzip -f -d "$SNAP_DATA/tmp/helm/helm.tar.gz"
  run_with_sudo tar -xf "$SNAP_DATA/tmp/helm/helm.tar")

  run_with_sudo mkdir -p "$SNAP_DATA/bin/"
  run_with_sudo mv "$SNAP_DATA/tmp/helm/linux-$(arch)/helm" "$SNAP_DATA/bin/helm"
  run_with_sudo chmod +x "$SNAP_DATA/bin/"
  run_with_sudo chmod +x "$SNAP_DATA/bin/helm"

  run_with_sudo rm -rf "$SNAP_DATA/tmp/helm"
fi

echo "Helm is enabled"
