#!/bin/bash

export INSTALL="${1}/bin"
mkdir -p "${INSTALL}"

snap refresh go --channel 1.18

make cluster-agent
cp cluster-agent "${INSTALL}"

snap refresh go --channel 1.16/stable
