#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh
CA_CERT=/snap/core18/current/etc/ssl/certs/ca-certificates.crt

echo "Enabling Istio"

if [ ! -f "${SNAP_DATA}/bin/istioctl" ]
then
  ISTIO_VERSION="v1.10.3"
  echo "Fetching istioctl version $ISTIO_VERSION."
  ISTIO_ERSION=$(echo $ISTIO_VERSION | sed 's/v//g')
  run_with_sudo mkdir -p "${SNAP_DATA}/tmp/istio"
  (cd "${SNAP_DATA}/tmp/istio"
  run_with_sudo "${SNAP}/usr/bin/curl" --cacert $CA_CERT -L https://github.com/istio/istio/releases/download/${ISTIO_ERSION}/istio-${ISTIO_ERSION}-linux-amd64.tar.gz -o "$SNAP_DATA/tmp/istio/istio.tar.gz"
  run_with_sudo gzip -q -d "$SNAP_DATA/tmp/istio/istio.tar.gz"
  run_with_sudo tar -xvf "$SNAP_DATA/tmp/istio/istio.tar"
  run_with_sudo chmod 777 "$SNAP_DATA/tmp/istio/istio-${ISTIO_ERSION}")
  run_with_sudo mkdir -p "$SNAP_DATA/bin/"
  run_with_sudo mv "$SNAP_DATA/tmp/istio/istio-${ISTIO_ERSION}/bin/istioctl" "$SNAP_DATA/bin/"
  run_with_sudo chmod +x "$SNAP_DATA/bin/"

  run_with_sudo rm -rf "$SNAP_DATA/tmp/istio"
fi

# pod/servicegraph will start failing without dns
"$SNAP/microk8s-enable.wrapper" dns

run_with_sudo "$SNAP_DATA/bin/istioctl" -c "${SNAP_DATA}/credentials/client.config" install --set profile=demo -y

run_with_sudo touch "$SNAP_USER_COMMON/istio.lock"

echo "Istio is starting"
echo ""
echo "To configure mutual TLS authentication consult the Istio documentation."
