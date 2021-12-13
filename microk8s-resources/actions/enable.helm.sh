#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Helm"

if [ ! -f "${SNAP_DATA}/bin/helm" ]
then
  SOURCE_URI="https://get.helm.sh"
  HELM_VERSION="v2.16.7"

  echo "Fetching helm version $HELM_VERSION."
  mkdir -p "/tmp/helm"
  (cd "/tmp/helm"
  curl -L $SOURCE_URI/helm-$HELM_VERSION-linux-$(arch).tar.gz -o "/tmp/helm/helm.tar.gz"
  gzip -f -d "/tmp/helm/helm.tar.gz"
  tar -xf "/tmp/helm/helm.tar" --no-same-owner)

  mkdir -p "$SNAP_DATA/bin/"
  mv "/tmp/helm/linux-$(arch)/helm" "$SNAP_DATA/bin/helm"
  chmod +x "$SNAP_DATA/bin/"
  chmod +x "$SNAP_DATA/bin/helm"

  rm -rf "/tmp/helm"
fi

echo "Helm is enabled"
