#!/bin/bash

INSTALL="${1}/bin"
mkdir -p "${INSTALL}"

export CGO_ENABLED=0

go build -ldflags "-s -w" -o migrator ./main.go

cp migrator "${INSTALL}/migrator"
