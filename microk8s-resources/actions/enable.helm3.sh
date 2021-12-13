#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Helm 3"

if [ ! -f "${SNAP_DATA}/bin/helm3" ]
then
  SOURCE_URI="https://get.helm.sh"
  HELM_VERSION="v3.5.0"

  echo "Fetching helm version $HELM_VERSION."
  mkdir -p "/tmp/helm"
  (cd "/tmp/helm"
  curl -L $SOURCE_URI/helm-$HELM_VERSION-linux-$(arch).tar.gz -o "/tmp/helm/helm.tar.gz"
  gzip -f -d "/tmp/helm/helm.tar.gz"
  tar -xf "/tmp/helm/helm.tar" --no-same-owner)

  mkdir -p "$SNAP_DATA/bin/"
  mv "/tmp/helm/linux-$(arch)/helm" "$SNAP_DATA/bin/helm3"
  chmod +x "$SNAP_DATA/bin/"
  chmod +x "$SNAP_DATA/bin/helm3"

  rm -rf "/tmp/helm"
fi

echo "Helm 3 is enabled"
