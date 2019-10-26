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
export FLANNELD_VERSION="${FLANNELD_VERSION:-v0.11.0}"
export CNI_VERSION="${CNI_VERSION:-v0.7.1}"
export KNATIVE_SERVING_VERSION="${KNATIVE_SERVING_VERSION:-v0.9.0}"
export KNATIVE_EVENTING_VERSION="${KNATIVE_EVENTING_VERSION:-v0.9.0}"
# RUNC commit matching the containerd release commit
# Tag 1.3.0
export CONTAINERD_COMMIT="${CONTAINERD_COMMIT:-36cf5b690dcc00ff0f34ff7799209050c3d0c59a}"
# Release v1.0.0~rc8+ with CVE-2019-16884 fix
export RUNC_COMMIT="${RUNC_COMMIT:-3e425f80a8c931f88e6d94a8c831b9d5aa481657}"
# Set this to the kubernetes fork you want to build binaries from
export KUBERNETES_REPOSITORY="${KUBERNETES_REPOSITORY:-}"
export KUBERNETES_COMMIT="${KUBERNETES_COMMIT:-}"

export KUBE_TRACK="${KUBE_TRACK:-}"

export KUBE_VERSION="${KUBE_VERSION:-}"
export KUBE_SNAP_BINS="${KUBE_SNAP_BINS:-}"
if [ -e "$KUBE_SNAP_BINS/version" ]; then
  export KUBE_VERSION=`cat $KUBE_SNAP_BINS/version`
else
  # KUBE_SNAP_BINS is not set meaning we will either build the binaries OR fetch them from upstream
  # eitherway the k8s binaries should land at build/kube_bins/$KUBE_VERSION
  if [ -z "$KUBE_VERSION" ]; then
    # KUBE_VERSION is not set we will probably need the one from the upstream repo. If we build from
    # source the KUBE_VERSION should be provided
    if [ -z "$KUBE_TRACK" ]; then
      export KUBE_VERSION="${KUBE_VERSION:-`curl -L https://dl.k8s.io/release/stable.txt`}"
    else
      export KUBE_VERSION="${KUBE_VERSION:-`curl -L https://dl.k8s.io/release/stable-${KUBE_TRACK}.txt`}"
    fi
  fi
fi

export KUBE_SNAP_ROOT="$(readlink -f .)"

echo "Building with:"
echo "KUBE_VERSION=${KUBE_VERSION}"
echo "ETCD_VERSION=${ETCD_VERSION}"
echo "FLANNELD_VERSION=${FLANNELD_VERSION}"
echo "CNI_VERSION=${CNI_VERSION}"
echo "KUBE_ARCH=${KUBE_ARCH}"
echo "KUBE_SNAP_BINS=${KUBE_SNAP_BINS}"
echo "KNATIVE_SERVING_VERSION=${KNATIVE_SERVING_VERSION}"
echo "KNATIVE_EVENTING_VERSION=${KNATIVE_EVENTING_VERSION}"
echo "RUNC_COMMIT=${RUNC_COMMIT}"
echo "CONTAINERD_COMMIT=${CONTAINERD_COMMIT}"
echo "KUBERNETES_REPOSITORY=${KUBERNETES_REPOSITORY}"
echo "KUBERNETES_COMMIT=${KUBERNETES_COMMIT}"
