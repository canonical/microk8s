#!/bin/bash -x

INSTALL="${1}/bin"
mkdir -p "${INSTALL}"

export PATH="${PATH}:$(go env GOPATH)/bin"
GO111MODULE=off go get github.com/containous/go-bindata/...

go generate
go build -ldflags "-s -w" ./cmd/traefik

cp traefik "${INSTALL}/traefik"
