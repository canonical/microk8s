#!/bin/bash

export INSTALL="${1}/bin"
mkdir -p "${INSTALL}"

make cluster-agent
cp cluster-agent "${INSTALL}"
