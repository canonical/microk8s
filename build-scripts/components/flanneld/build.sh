#!/bin/bash

INSTALL="${1}/opt/cni/bin"
mkdir -p "${INSTALL}"

VERSION="${2}"

export CGO_ENABLED=0
go build -o dist/flanneld -ldflags "-s -w -X github.com/flannel-io/flannel/version.Version=${VERSION} -extldflags -static"

cp dist/flanneld "${INSTALL}/flanneld"
