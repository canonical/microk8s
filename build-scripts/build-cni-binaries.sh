#!/bin/bash
set -eux

echo "Building cni binaries for $CNI_VERSION"
export CNI_SNAP_BINS="build/cni_bins"
mkdir -p $CNI_SNAP_BINS
export GOPATH=$SNAPCRAFT_PART_BUILD/go

rm -rf $GOPATH
mkdir -p $GOPATH

git clone --depth 1 https://github.com/containernetworking/plugins $GOPATH/src/github.com/containernetworking/plugins -b $CNI_VERSION

rm -rf $SNAPCRAFT_PART_SRC/eks-distro
git clone --depth 1 https://github.com/aws/eks-distro $SNAPCRAFT_PART_SRC/eks-distro

(cd $GOPATH/src/github.com/containernetworking/plugins
  git config user.email "microk8s-builder-bot@ubuntu.com"
  git config user.name "MicroK8s builder bot"

  for patch in "${SNAPCRAFT_PART_SRC}"/eks-distro/projects/containernetworking/plugins/patches/*.patch
  do
    echo "Applying patch $patch"
    git am < "$patch"
  done

  ORG_PATH="github.com/containernetworking"
  export REPO_PATH="${ORG_PATH}/plugins"
  export GOFLAGS="-mod=vendor"
  export GO="${GO:-go}"

  echo "Building plugins"
  PLUGINS="plugins/meta/* plugins/main/* plugins/ipam/*"
  for d in $PLUGINS; do
      if [ -d "$d" ]; then
          plugin="$(basename "$d")"
          if [ $plugin != "windows" ]; then
              echo "  $plugin"
              $GO build -o "bin/$plugin" "$@" "$REPO_PATH"/$d
          fi
      fi
  done
)

cp $GOPATH/src/github.com/containernetworking/plugins/bin/* $CNI_SNAP_BINS/