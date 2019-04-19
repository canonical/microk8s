#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

read -ra ARGUMENTS <<< "$1"
argz=("${ARGUMENTS[@]/#/--}")

# check if linkerd cli is already in the system.  Download if it doesn't exist.
if [ ! -f "${SNAP_DATA}/bin/linkerd" ]; then
  LINKERD_VERSION="${LINKERD_VERSION:-v2.3.0}"
  echo "Fetching Linkerd2 version $LINKERD_VERSION."
  sudo mkdir -p "$SNAP_DATA/bin"
  LINKERD_VERSION=$(echo $LINKERD_VERSION | sed 's/v//g')
  echo "$LINKERD_VERSION"
  sudo "${SNAP}/usr/bin/curl" -L https://github.com/linkerd/linkerd2/releases/download/stable-${LINKERD_VERSION}/linkerd2-cli-stable-${LINKERD_VERSION}-linux -o "$SNAP_DATA/bin/linkerd"
  sudo chmod uo+x "$SNAP_DATA/bin/linkerd"
fi 

echo "Enabling Linkerd2"
# pod/servicegraph will start failing without dns
"$SNAP/microk8s-enable.wrapper" dns
"$SNAP_DATA/bin/linkerd" "--kubeconfig=$SNAP/client.config" install "${argz[@]}" | "$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply -f -
echo "Linkerd is starting"