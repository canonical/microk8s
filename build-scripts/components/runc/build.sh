#!/bin/bash

export INSTALL="${1}/bin"
mkdir -p "${INSTALL}"

export CGO_ENABLED=1
export GOEXPERIMENT=opensslcrypto
make BUILDTAGS="seccomp apparmor" EXTRA_LDFLAGS="-s -w"
cp runc "${INSTALL}/runc"
