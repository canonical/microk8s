#!/usr/bin/env bash

set -ex

source $SNAP/actions/common/utils.sh
CA_CERT=/snap/core/current/etc/ssl/certs/ca-certificates.crt

read -ra ARGUMENTS <<< "$1"
argz=("${ARGUMENTS[@]/#/--}")

# check if linkerd cli is already in the system.  Download if it doesn't exist.
if [ ! -f "${SNAP_DATA}/bin/linkerd" ]; then
  LINKERD_VERSION="${LINKERD_VERSION:-v2.6.0}"
  echo "Fetching Linkerd2 version $LINKERD_VERSION."
  run_with_sudo mkdir -p "$SNAP_DATA/bin"
  LINKERD_VERSION=$(echo $LINKERD_VERSION | sed 's/v//g')
  echo "$LINKERD_VERSION"
  run_with_sudo "${SNAP}/usr/bin/curl" --cacert $CA_CERT -L https://github.com/linkerd/linkerd2/releases/download/stable-${LINKERD_VERSION}/linkerd2-cli-stable-${LINKERD_VERSION}-linux -o "$SNAP_DATA/bin/linkerd"
  run_with_sudo chmod uo+x "$SNAP_DATA/bin/linkerd"
fi

echo "Enabling Linkerd2"
# enable dns service
KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
"$SNAP/microk8s-enable.wrapper" dns
# Allow some time for the apiserver to start
sleep 5
${SNAP}/microk8s-status.wrapper --wait-ready --timeout 30 >/dev/null


"$SNAP_DATA/bin/linkerd" "--kubeconfig=$SNAP_DATA/credentials/client.config" install "${argz[@]}" | $KUBECTL apply -f -
echo "Linkerd is starting"
