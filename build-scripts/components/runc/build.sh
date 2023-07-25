#!/bin/bash

export INSTALL="${1}/bin"
mkdir -p "${INSTALL}"

make BUILDTAGS="seccomp apparmor" EXTRA_LDFLAGS="-s -w" static
cp runc "${INSTALL}/runc"
