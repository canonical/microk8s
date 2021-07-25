#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Istio"

run_with_sudo "${SNAP_DATA}/bin/istioctl" -c "${SNAP_DATA}/credentials/client.config" x uninstall --purge -y
run_with_sudo rm -rf "${SNAP_DATA}/bin/istioctl"
run_with_sudo rm -rf "$SNAP_USER_COMMON/istio-auth.lock"
run_with_sudo rm -rf "$SNAP_USER_COMMON/istio.lock"

echo "Istio is terminating"
