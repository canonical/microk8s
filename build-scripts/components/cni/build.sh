#!/bin/bash

INSTALL="${1}/opt/cni/bin"
mkdir -p "${INSTALL}"

./build_linux.sh

cp bin/* "${INSTALL}/"
