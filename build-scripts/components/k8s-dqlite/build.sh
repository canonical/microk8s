#!/bin/bash

INSTALL="${1}/bin"
mkdir -p "${INSTALL}"

# Temporarily pin Go version to 1.19.5 to deal with TLS session resumption issues
ARCH="$(arch)"
case "$ARCH" in
  x86_64) ARCH=amd64 ;;
  aarch64) ARCH=arm64 ;;
esac

if [ ! -f go/bin/go ]; then
  curl -LO "https://go.dev/dl/go1.19.5.linux-${ARCH}.tar.gz"
  tar xvzf "go1.19.5.linux-${ARCH}.tar.gz"
fi

export CGO_LDFLAGS_ALLOW="-Wl,-z,now"
export CGO_CFLAGS="-I${SNAPCRAFT_STAGE}/usr/include/"
export CGO_LDFLAGS="-L${SNAPCRAFT_STAGE}/lib"

GOPATH="$PWD/go" ./go/bin/go build -ldflags "-s -w" -tags libsqlite3,dqlite .

cp k8s-dqlite "${INSTALL}/k8s-dqlite"
