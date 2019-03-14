#!/usr/bin/env bash
set -eu

export ARCH="${KUBE_ARCH:-`dpkg --print-architecture`}"
KUBE_ARCH=${ARCH}
SNAP_ARCH=${KUBE_ARCH}
if [ "$ARCH" = "ppc64el" ]; then
  KUBE_ARCH="ppc64le"
elif [ "$ARCH" = "armhf" ]; then
  KUBE_ARCH="arm"
fi
export KUBE_ARCH

export ETCD_VERSION="${ETCD_VERSION:-v3.3.4}"
export CNI_VERSION="${CNI_VERSION:-v0.7.1}"
export ISTIO_VERSION="${ISTIO_VERSION:-v1.0.5}"
# RUNC commit matching the containerd release commit
# Tag 1.2.4
export CONTAINERD_COMMIT="${CONTAINERD_COMMIT:-e6b3f5632f50dbc4e9cb6288d911bf4f5e95b18e}"
# Release v1.0.0~rc6 with CVE-2019-5736 fix
export RUNC_COMMIT="${RUNC_COMMIT:-6635b4f0c6af3810594d2770f662f34ddc15b40d}"

export KUBE_TRACK="${KUBE_TRACK:-}"
export KUBE_SNAP_BINS="${KUBE_SNAP_BINS:-}"
if [ -z "$KUBE_SNAP_BINS" ]; then
  if [ -z "$KUBE_TRACK" ]; then
    export KUBE_VERSION="${KUBE_VERSION:-`curl -L https://dl.k8s.io/release/stable.txt`}"
  else
    export KUBE_VERSION="${KUBE_VERSION:-`curl -L https://dl.k8s.io/release/stable-${KUBE_TRACK}.txt`}"
  fi
else
  export KUBE_VERSION=`cat $KUBE_SNAP_BINS/version`
fi

export KUBE_SNAP_ROOT="$(readlink -f .)"

echo "Building with:"
echo "KUBE_VERSION=${KUBE_VERSION}"
echo "ETCD_VERSION=${ETCD_VERSION}"
echo "CNI_VERSION=${CNI_VERSION}"
echo "KUBE_ARCH=${KUBE_ARCH}"
echo "KUBE_SNAP_BINS=${KUBE_SNAP_BINS}"
echo "ISTIO_VERSION=${ISTIO_VERSION}"
echo "RUNC_COMMIT=${RUNC_COMMIT}"
echo "CONTAINERD_COMMIT=${CONTAINERD_COMMIT}"
