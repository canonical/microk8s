#!/bin/bash

export INSTALL="${1}/bin"
mkdir -p "${INSTALL}"

make crictl
cp build/bin/crictl "${INSTALL}/crictl"
