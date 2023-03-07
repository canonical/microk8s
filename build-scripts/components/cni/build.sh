#!/bin/bash

VERSION="${2}"

INSTALL="${1}/opt/cni/bin"
mkdir -p "${INSTALL}"

# these would very tedious to apply with a patch
go get github.com/docker/docker/pkg/reexec
go get github.com/flannel-io/cni-plugin@v1.1.2
go get -t github.com/containernetworking/plugins/integration
rm -rf plugins/meta/flannel
git clone --depth 1 --branch v1.1.2 https://github.com/flannel-io/cni-plugin.git plugins/meta/flannel
go mod edit -replace github.com/flannel-io/cni-plugin@v1.1.2=./plugins/meta/flannel
sed -i 's/^package main/package plugin_main/' plugins/*/*/*.go
sed -i 's/^func main()/func Main()/' plugins/*/*/*.go
go mod vendor

export CGO_ENABLED=0

go build -o cni -ldflags "-s -w -extldflags -static -X github.com/containernetworking/plugins/pkg/utils/buildversion.BuildVersion=${VERSION}" ./cni.go

cp cni "${INSTALL}/"
for plugin in dhcp host-local static bridge host-device ipvlan loopback macvlan ptp vlan bandwidth flannel firewall portmap sbr tuning vrf; do
  ln -f -s ./cni "${INSTALL}/${plugin}"
done
