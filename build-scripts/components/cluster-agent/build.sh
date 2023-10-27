#!/bin/bash

export INSTALL="${1}/bin"
mkdir -p "${INSTALL}"

export GOEXPERIMENT=opensslcrypto
export CGO_ENABLED=1
go build -ldflags '-s -w' -o cluster-agent ./main.go

cp cluster-agent "${INSTALL}"
