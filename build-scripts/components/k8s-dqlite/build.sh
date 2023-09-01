#!/bin/bash

INSTALL="${1}/bin"
mkdir -p "${INSTALL}"

make static -j

cp bin/static/dqlite "${INSTALL}/dqlite"
cp bin/static/k8s-dqlite "${INSTALL}/k8s-dqlite"
