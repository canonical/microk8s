#!/bin/bash

INSTALL="${1}/bin"
mkdir -p "${INSTALL}"

go build -ldflags "-s -w" -o migrator ./main.go

cp migrator "${INSTALL}/migrator"
