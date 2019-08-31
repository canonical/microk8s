#!/bin/bash
set -eu

echo "Building k8s bianries from $KUBERNETES_REPOSITORY commit $KUBERNETES_COMMIT"
apps="kubectl kube-apiserver kube-controller-manager kube-scheduler kubelet kube-proxy"
path_apps="cmd/kubectl cmd/kube-apiserver cmd/kube-controller-manager cmd/kube-scheduler cmd/kubelet cmd/kube-proxy"
export KUBE_SNAP_BINS="build/kube_bins/$KUBE_VERSION"
mkdir -p $KUBE_SNAP_BINS/$KUBE_ARCH

export GOPATH=$(dirname $SNAPCRAFT_PART_INSTALL)/go
mkdir -p $GOPATH

go get -d $KUBERNETES_REPOSITORY || true

(cd $GOPATH/src/$KUBERNETES_REPOSITORY
  git checkout $KUBERNETES_COMMIT
  make clean && make WHAT="${path_apps}"
)
for app in $apps; do
  cp $GOPATH/src/$KUBERNETES_REPOSITORY/_output/bin/$app $KUBE_SNAP_BINS/$KUBE_ARCH/
done
