#!/bin/bash

export INSTALL="${1}/bin"
export GOEXPERIMENT=opensslcrypto
mkdir -p "${INSTALL}"

CGO_ENABLED=1 go build -ldflags '-s -w' -o cluster-agent ./main.go
cp cluster-agent "${INSTALL}"
