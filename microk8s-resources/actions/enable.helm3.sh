#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh
CA_CERT=/snap/core/current/etc/ssl/certs/ca-certificates.crt

echo "Enabling Helm 3"

if [ ! -f "${SNAP_DATA}/bin/helm3" ]
then
  SOURCE_URI="https://get.helm.sh"
  HELM_VERSION="v3.0.2"

  echo "Fetching helm version $HELM_VERSION."
  mkdir -p "${SNAP_DATA}/tmp/helm"
  (cd "${SNAP_DATA}/tmp/helm"
  "${SNAP}/usr/bin/curl" --cacert $CA_CERT -L $SOURCE_URI/helm-$HELM_VERSION-linux-$(arch).tar.gz -o "$SNAP_DATA/tmp/helm/helm.tar.gz"
  gzip -f -d "$SNAP_DATA/tmp/helm/helm.tar.gz"
  tar -xf "$SNAP_DATA/tmp/helm/helm.tar")

  mkdir -p "$SNAP_DATA/bin/"
  mv "$SNAP_DATA/tmp/helm/linux-$(arch)/helm" "$SNAP_DATA/bin/helm3"
  chmod +x "$SNAP_DATA/bin/"
  chmod +x "$SNAP_DATA/bin/helm3"

  rm -rf "$SNAP_DATA/tmp/helm"
fi

echo "Helm 3 is enabled"
