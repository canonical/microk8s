#!/bin/bash
set -eux

echo "Building k8s bianries from $KUBERNETES_REPOSITORY tag $KUBERNETES_TAG"
apps="kubectl kube-apiserver kube-controller-manager kube-scheduler kubelet kube-proxy"
path_apps="cmd/kubectl cmd/kube-apiserver cmd/kube-controller-manager cmd/kube-scheduler cmd/kubelet cmd/kube-proxy"
export KUBE_SNAP_BINS="build/kube_bins/$KUBE_VERSION"
mkdir -p $KUBE_SNAP_BINS/$KUBE_ARCH

export GOPATH=$SNAPCRAFT_PART_INSTALL/go
mkdir -p $GOPATH

go get -d $KUBERNETES_REPOSITORY || true

(cd $GOPATH/src/$KUBERNETES_REPOSITORY
  git checkout $KUBERNETES_TAG
  for patch in "${SNAPCRAFT_PROJECT_DIR}"/build-scripts/patches/*.patch
  do
    [[ -e "$patch" ]] || break
    echo "Applying patch $patch"
    git am < "${SNAPCRAFT_PROJECT_DIR}/build-scripts/patches/$patch"
  done

  rm -rf $GOPATH/src/$KUBERNETES_REPOSITORY/_output/
  make clean
  for app in ${path_apps}
  do
    make WHAT="${app}" GOFLAGS=-tags=libsqlite3 CGO_CFLAGS="-I${SNAPCRAFT_STAGE}/usr/include/" CGO_LDFLAGS="-L${SNAPCRAFT_STAGE}/lib" KUBE_CGO_OVERRIDES=kube-apiserver
  done
)
for app in $apps; do
  cp $GOPATH/src/$KUBERNETES_REPOSITORY/_output/bin/$app $KUBE_SNAP_BINS/$KUBE_ARCH/
done
