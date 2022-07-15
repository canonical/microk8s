#!/bin/bash

INSTALL="${1}/opt/cni/bin"
mkdir -p "${INSTALL}"

# TODO(neoaggelos): update to a non-ancient version of flanneld that we can actually build
FLANNELD_VERSION="v0.11.0"
ARCH="${ARCH:-`dpkg --print-architecture`}"
if [ "$ARCH" = "ppc64el" ]; then
  ARCH="ppc64le"
elif [ "$ARCH" = "armhf" ]; then
  ARCH="arm"
fi
mkdir -p download
cd download
curl -LO https://github.com/coreos/flannel/releases/download/${FLANNELD_VERSION}/flannel-${FLANNELD_VERSION}-linux-${ARCH}.tar.gz
tar xvzf flannel-*.tar.gz

cp flanneld "${INSTALL}/flanneld"
