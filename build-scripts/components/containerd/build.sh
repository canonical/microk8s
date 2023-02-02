#!/bin/bash

INSTALL="${1}/bin"
mkdir -p "${INSTALL}"

for bin in ctr containerd containerd-shim containerd-shim-runc-v1 containerd-shim-runc-v2; do
  make "bin/${bin}"
  cp "bin/${bin}" "${INSTALL}/${bin}"
done
