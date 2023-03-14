#!/bin/bash

INSTALL="${1}/bin"
mkdir -p "${INSTALL}"

VERSION="${2}"
REVISION=$(git rev-parse HEAD)

sed -i "s,^VERSION.*$,VERSION=${VERSION}," Makefile
sed -i "s,^REVISION.*$,REVISION=${REVISION}," Makefile

export STATIC=1
for bin in ctr containerd containerd-shim containerd-shim-runc-v1 containerd-shim-runc-v2; do
  make "bin/${bin}"
  cp "bin/${bin}" "${INSTALL}/${bin}"
done
