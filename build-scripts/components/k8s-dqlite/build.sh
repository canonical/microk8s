#!/bin/bash

INSTALL="${1}"
mkdir -p "${INSTALL}/bin" "${INSTALL}/usr/lib"

export GOEXPERIMENT=opensslcrypto
make dynamic -j

cp bin/dynamic/dqlite "${INSTALL}/bin/dqlite"
cp bin/dynamic/k8s-dqlite "${INSTALL}/bin/k8s-dqlite"
cp bin/dynamic/lib/*so* "${INSTALL}/usr/lib"
