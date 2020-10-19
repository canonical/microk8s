#!/bin/bash
set -eux

echo "Building k8s binaries from $KUBERNETES_REPOSITORY tag $KUBERNETES_TAG"
apps="kubectl kube-apiserver kube-controller-manager kube-scheduler kubelet kube-proxy"
path_apps="cmd/kubectl cmd/kube-apiserver cmd/kube-controller-manager cmd/kube-scheduler cmd/kubelet cmd/kube-proxy"
export KUBE_SNAP_BINS="build/kube_bins/$KUBE_VERSION"
mkdir -p $KUBE_SNAP_BINS/$KUBE_ARCH
echo $KUBE_VERSION > $KUBE_SNAP_BINS/version

export GOPATH=$SNAPCRAFT_PART_BUILD/go

rm -rf $GOPATH
mkdir -p $GOPATH

git clone --depth 1 https://github.com/kubernetes/kubernetes $GOPATH/src/github.com/kubernetes/kubernetes/ -b $KUBERNETES_TAG

(cd $GOPATH/src/$KUBERNETES_REPOSITORY
  git config user.email "microk8s-builder-bot@ubuntu.com"
  git config user.name "MicroK8s builder bot"

  PATCHES="patches"
  if echo "$KUBE_VERSION" | grep -e beta -e rc -e alpha
  then
    PATCHES="pre-patches"
  fi

  for patch in "${SNAPCRAFT_PROJECT_DIR}"/build-scripts/"$PATCHES"/*.patch
  do
    echo "Applying patch $patch"
    git am < "$patch"
  done

  rm -rf $GOPATH/src/$KUBERNETES_REPOSITORY/_output/
  make clean
  for app in ${path_apps}
  do
    if [ "$app" = "cmd/kube-apiserver" ]
    then
      make WHAT="${app}" GOFLAGS=-tags=libsqlite3,dqlite CGO_CFLAGS="-I${SNAPCRAFT_STAGE}/usr/include/" CGO_LDFLAGS="-L${SNAPCRAFT_STAGE}/lib" KUBE_CGO_OVERRIDES=kube-apiserver
    else
      make WHAT="${app}"
    fi
  done
)
for app in $apps; do
  cp $GOPATH/src/$KUBERNETES_REPOSITORY/_output/bin/$app $KUBE_SNAP_BINS/$KUBE_ARCH/
done

rm -rf $GOPATH/src/$KUBERNETES_REPOSITORY/_output/
