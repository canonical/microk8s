#!/bin/bash

export INSTALL="${1}"
mkdir -p "${INSTALL}"

GO_LDFLAGS="-s -w" GO_BUILD_FLAGS="-v" ./build.sh

for bin in etcd etcdctl; do
  cp "bin/${bin}" "${INSTALL}/${bin}"
done
