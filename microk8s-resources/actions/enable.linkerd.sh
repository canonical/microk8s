#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Linkerd is not yet available in v1.16 MicroK8s. Please install the v1.15 release:"
echo ""
echo "sudo snap install microk8s --classic --channel=1.15/stable"
echo ""
exit 1

read -ra ARGUMENTS <<< "$1"
argz=("${ARGUMENTS[@]/#/--}")

# check if linkerd cli is already in the system.  Download if it doesn't exist.
if [ ! -f "${SNAP_DATA}/bin/linkerd" ]; then
  LINKERD_VERSION="${LINKERD_VERSION:-v2.4.0}"
  echo "Fetching Linkerd2 version $LINKERD_VERSION."
  sudo mkdir -p "$SNAP_DATA/bin"
  LINKERD_VERSION=$(echo $LINKERD_VERSION | sed 's/v//g')
  echo "$LINKERD_VERSION"
  sudo "${SNAP}/usr/bin/curl" -L https://github.com/linkerd/linkerd2/releases/download/stable-${LINKERD_VERSION}/linkerd2-cli-stable-${LINKERD_VERSION}-linux -o "$SNAP_DATA/bin/linkerd"
  sudo chmod uo+x "$SNAP_DATA/bin/linkerd"
fi 

echo "Enabling Linkerd2"
# pod/servicegraph will start failing without dns
KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
"$SNAP/microk8s-enable.wrapper" dns
# Allow some time for the apiserver to start
sleep 5

"$SNAP_DATA/bin/linkerd" "--kubeconfig=$SNAP_DATA/credentials/client.config" install "${argz[@]}" | $KUBECTL apply -f -
echo "Linkerd is starting"
