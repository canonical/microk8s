#!/bin/bash

export INSTALL="${1}/bin"
export GOEXPERIMENT=opensslcrypto
mkdir -p "${INSTALL}"

make cluster-agent
cp cluster-agent "${INSTALL}"
