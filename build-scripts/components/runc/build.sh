#!/bin/bash

export INSTALL="${1}/bin"
mkdir -p "${INSTALL}"

export SHIM_CGO_ENABLED=1
make BUILDTAGS="seccomp apparmor" EXTRA_LDFLAGS="-s -w"
cp runc "${INSTALL}/runc"
