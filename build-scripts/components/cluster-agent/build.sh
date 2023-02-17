#!/bin/bash

export INSTALL="${1}/bin"
export GOEXPERIMENT=opensslcrypto
mkdir -p "${INSTALL}"

go mod tidy
CGO_ENABLED=1 go build -o cluster-agent ./main.go
cp cluster-agent "${INSTALL}"
