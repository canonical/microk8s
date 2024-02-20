#!/bin/bash

VERSION="${2}"

export INSTALL="${1}/bin"
mkdir -p "${INSTALL}"

# Ensure `runc --version` prints the correct release commit
export COMMIT="$(git describe --always --long "${VERSION}")"

make BUILDTAGS="seccomp apparmor" EXTRA_LDFLAGS="-s -w" static
cp runc "${INSTALL}/runc"
