#!/bin/bash

INSTALL="${1}/bin"
mkdir -p "${INSTALL}"

export CGO_CFLAGS="-I${SNAPCRAFT_STAGE}/usr/include/"
export CGO_LDFLAGS="-L${SNAPCRAFT_STAGE}/lib"
export LD_LIBRARY_PATH="${SNAPCRAFT_STAGE}/lib"

go build -ldflags "-s -w" -tags libsqlite3,dqlite .

cp k8s-dqlite "${INSTALL}/k8s-dqlite"
