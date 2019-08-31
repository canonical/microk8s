#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Helm"

if [ ! -f "${SNAP_DATA}/bin/helm" ]
then
  SOURCE_URI="https://get.helm.sh"
  HELM_VERSION="v2.14.3"

  echo "Fetching helm version $HELM_VERSION."
  sudo mkdir -p "${SNAP_DATA}/tmp/helm"
  (cd "${SNAP_DATA}/tmp/helm"
  sudo "${SNAP}/usr/bin/curl" -L $SOURCE_URI/helm-$HELM_VERSION-linux-$(arch).tar.gz -o "$SNAP_DATA/tmp/helm/helm.tar.gz"
  sudo gzip -f -d "$SNAP_DATA/tmp/helm/helm.tar.gz"
  sudo tar -xf "$SNAP_DATA/tmp/helm/helm.tar")

  sudo mkdir -p "$SNAP_DATA/bin/"
  sudo mv "$SNAP_DATA/tmp/helm/linux-$(arch)/helm" "$SNAP_DATA/bin/helm"
  sudo chmod +x "$SNAP_DATA/bin/"
  sudo chmod +x "$SNAP_DATA/bin/helm"

  sudo rm -rf "$SNAP_DATA/tmp/helm"
fi

echo "Helm is enabled"
