#!/bin/bash

export INSTALL="${1}/bin"
mkdir -p "${INSTALL}"
export GOEXPERIMENT=opensslcrypto

make crictl
cp build/bin/crictl "${INSTALL}/crictl"
