#!/usr/bin/env bash
set -eu

export KUBE_ARCH="${KUBE_ARCH:-`dpkg --print-architecture`}"
SNAP_ARCH=${KUBE_ARCH}
if [ "$KUBE_ARCH" == "ppc64el" ]; then
  SNAP_ARCH="ppc64le"
elif [ "$KUBE_ARCH" == "arm" ]; then
  SNAP_ARCH="armhf"
fi
export SNAP_ARCH

export ETCD_VERSION="${ETCD_VERSION:-v3.3.4}"
export CNI_VERSION="${CNI_VERSION:-v0.6.0}"

export KUBE_SNAP_BINS="${KUBE_SNAP_BINS:-}"
if [ -z "$KUBE_SNAP_BINS" ]; then
  export KUBE_VERSION="${KUBE_VERSION:-`curl -L https://dl.k8s.io/release/stable.txt`}"
else
  export KUBE_VERSION=`cat $KUBE_SNAP_BINS/version`
fi

export KUBE_SNAP_ROOT="$(readlink -f .)"

echo "Building with:"
echo "KUBE_VERSION=${KUBE_VERSION}"
echo "ETCD_VERSION=${ETCD_VERSION}"
echo "CNI_VERSION=${CNI_VERSION}"
echo "KUBE_ARCH=${KUBE_ARCH}"
echo "SNAP_ARCH=${SNAP_ARCH}"
echo "KUBE_SNAP_BINS=${KUBE_SNAP_BINS}"
