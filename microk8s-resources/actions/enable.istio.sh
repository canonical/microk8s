#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Istio"

if [ ! -f "${SNAP_DATA}/bin/istioctl" ]
then
  ISTIO_VERSION="v1.10.3"
  echo "Fetching istioctl version $ISTIO_VERSION."
  ISTIO_ERSION=$(echo $ISTIO_VERSION | sed 's/v//g')
  mkdir -p "/tmp/istio"
  (cd "/tmp/istio"
  "${SNAP}/usr/bin/curl" -L https://github.com/istio/istio/releases/download/${ISTIO_ERSION}/istio-${ISTIO_ERSION}-linux-amd64.tar.gz -o "/tmp/istio/istio.tar.gz"
  gzip -q -d "/tmp/istio/istio.tar.gz"
  tar -xvf "/tmp/istio/istio.tar"
  chmod 777 "/tmp/istio/istio-${ISTIO_ERSION}")
  mkdir -p "$SNAP_DATA/bin/"
  mv "/tmp/istio/istio-${ISTIO_ERSION}/bin/istioctl" "$SNAP_DATA/bin/"
  chmod +x "$SNAP_DATA/bin/"

  rm -rf "/tmp/istio"
fi

# pod/servicegraph will start failing without dns
"$SNAP/microk8s-enable.wrapper" dns

"$SNAP_DATA/bin/istioctl" -c "${SNAP_DATA}/credentials/client.config" install --set profile=demo -y

touch "$SNAP_USER_COMMON/istio.lock"

echo "Istio is starting"
echo ""
echo "To configure mutual TLS authentication consult the Istio documentation."
