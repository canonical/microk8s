#!/bin/bash

VERSION="${2}"

INSTALL="${1}/opt/cni/bin"
mkdir -p "${INSTALL}"

DIR=`realpath $(dirname "${0}")`
GIT_TAG="$("${DIR}/version.sh")"

if [ ! -d "${SNAPCRAFT_PART_BUILD}/eks-distro" ]; then
  git clone --depth 1 https://github.com/aws/eks-distro $SNAPCRAFT_PART_BUILD/eks-distro
else
  (cd $SNAPCRAFT_PART_BUILD/eks-distro && git fetch --all && git pull)
fi

for patch in "${SNAPCRAFT_PART_BUILD}"/eks-distro/projects/containernetworking/plugins/patches/*.patch
do
  echo "Applying patch $patch"
  git am < "$patch"
done

# these would very tedious to apply with a patch
go get github.com/docker/docker/pkg/reexec
go mod vendor
sed -i 's/^package main/package plugin_main/' plugins/*/*/*.go
sed -i 's/^func main()/func Main()/' plugins/*/*/*.go

export CGO_ENABLED=0

go build -o cni -ldflags "-s -w -extldflags -static -X github.com/containernetworking/plugins/pkg/utils/buildversion.BuildVersion=${VERSION}" ./cni.go

cp cni "${INSTALL}/"
for plugin in dhcp host-local static bridge host-device ipvlan loopback macvlan ptp vlan bandwidth flannel firewall portmap sbr tuning; do
  ln -f -s ./cni "${INSTALL}/${plugin}"
done
