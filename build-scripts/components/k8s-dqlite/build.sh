#!/bin/bash

INSTALL="${1}/bin"
mkdir -p "${INSTALL}"

make go.build.static
make migrator
make dqlite

cp migrator "${INSTALL}/migrator"
cp dqlite "${INSTALL}/dqlite"
cp k8s-dqlite "${INSTALL}/k8s-dqlite"
