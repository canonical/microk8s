#!/bin/bash

export INSTALL="${1}"
mkdir -p "${INSTALL}"

sed -i 's/CGO_ENABLED=0/CGO_ENABLED=1/' build.sh
GOEXPERIMENT=opensslcrypto GO_LDFLAGS="-s -w" GO_BUILD_FLAGS="-v" ./build.sh

for bin in etcd etcdctl; do
  cp "bin/${bin}" "${INSTALL}/${bin}"
done
