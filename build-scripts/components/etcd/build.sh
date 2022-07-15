#!/bin/bash

export INSTALL="${1}"
mkdir -p "${INSTALL}"

GO_LDFLAGS="-s -w" make

for bin in etcd etcdctl; do
  cp "bin/${bin}" "${INSTALL}/${bin}"
done
