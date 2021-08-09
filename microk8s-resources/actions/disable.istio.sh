#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling Istio"

"${SNAP_DATA}/bin/istioctl" -c "${SNAP_DATA}/credentials/client.config" x uninstall --purge -y
rm -rf "${SNAP_DATA}/bin/istioctl"
rm -rf "$SNAP_USER_COMMON/istio-auth.lock"
rm -rf "$SNAP_USER_COMMON/istio.lock"

echo "Istio is terminating"
