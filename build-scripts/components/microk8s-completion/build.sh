#!/bin/bash

INSTALL="${1}"

snap refresh go --channel 1.18

go mod tidy -compat=1.17
go run -tags microk8s_hack ./cmd/helm 2> /dev/null

cp microk8s.bash "${INSTALL}/microk8s.bash"

snap refresh go --channel 1.16/stable