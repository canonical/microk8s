#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

# check if linkerd is already in the system.
if [ ! -f "${SNAP_DATA}/bin/linkerd" ]; then

  LINKERD_VERSION="${LINKERD_VERSION:-v2.2.1}"
  echo "Fetching Linkerd2 version $LINKERD_VERSION."

  mkdir -p "$SNAP_DATA/bin"
  LINKERD_VERSION=$(echo $LINKERD_VERSION | sed 's/v//g')
  echo "$LINKERD_VERSION"
  curl -L https://github.com/linkerd/linkerd2/releases/download/stable-${LINKERD_VERSION}/linkerd2-cli-stable-${LINKERD_VERSION}-linux -o "$SNAP_DATA/bin/linkerd"
  chmod +x "$SNAP_DATA/bin/linkerd"

fi 

echo "Enabling Linkerd2"

# pod/servicegraph will start failing without dns
#"$SNAP/microk8s-enable.wrapper" dns

"$SNAP_DATA/bin/linkerd" install "$*" | "$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" apply -f -

echo "Linkerd is starting"
