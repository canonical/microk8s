#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh
CA_CERT=/snap/core/current/etc/ssl/certs/ca-certificates.crt

echo "Enabling Istio"

if [ ! -f "${SNAP_DATA}/bin/istioctl" ]
then
  ISTIO_VERSION="v1.2.2"
  echo "Fetching istioctl version $ISTIO_VERSION."
  ISTIO_ERSION=$(echo $ISTIO_VERSION | sed 's/v//g')
  sudo mkdir -p "${SNAP_DATA}/tmp/istio"
  (cd "${SNAP_DATA}/tmp/istio"
  sudo "${SNAP}/usr/bin/curl" --cacert $CA_CERT -L https://github.com/istio/istio/releases/download/${ISTIO_ERSION}/istio-${ISTIO_ERSION}-linux.tar.gz -o "$SNAP_DATA/tmp/istio/istio.tar.gz"
  sudo gzip -d "$SNAP_DATA/tmp/istio/istio.tar.gz"
  sudo tar -xvf "$SNAP_DATA/tmp/istio/istio.tar")
  sudo mkdir -p "$SNAP_DATA/bin/"
  sudo mv "$SNAP_DATA/tmp/istio/istio-${ISTIO_ERSION}/bin/istioctl" "$SNAP_DATA/bin/"
  sudo chmod +x "$SNAP_DATA/bin/"

  sudo mkdir -p "$SNAP_DATA/actions/istio/"

  sudo cp "$SNAP_DATA/tmp/istio/istio-${ISTIO_ERSION}"/install/kubernetes/helm/istio-init/files/crd*.yaml "$SNAP_DATA/actions/istio/"
  sudo mv "$SNAP_DATA/tmp/istio/istio-${ISTIO_ERSION}/install/kubernetes/istio-demo-auth.yaml" "$SNAP_DATA/actions/istio/"
  sudo mv "$SNAP_DATA/tmp/istio/istio-${ISTIO_ERSION}/install/kubernetes/istio-demo.yaml" "$SNAP_DATA/actions/istio/"

  sudo rm -rf "$SNAP_DATA/tmp/istio"
fi

# pod/servicegraph will start failing without dns
"$SNAP/microk8s-enable.wrapper" dns

read -p "Enforce mutual TLS authentication (https://bit.ly/2KB4j04) between sidecars? If unsure, choose N. (y/N): " confirm

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
for i in "${SNAP_DATA}"/actions/istio/crd*yaml
do
  $KUBECTL apply -f "$i"
done

if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]
then
  $KUBECTL apply -f "${SNAP_DATA}/actions/istio/istio-demo-auth.yaml"
  sudo touch "$SNAP_USER_COMMON/istio-auth.lock"
else
  $KUBECTL apply -f "${SNAP_DATA}/actions/istio/istio-demo.yaml"
  sudo touch "$SNAP_USER_COMMON/istio.lock"
fi

refresh_opt_in_config "allow-privileged" "true" kube-apiserver
sudo snapctls restart ${SNAP_NAME}.daemon-apiserver

echo "Istio is starting"
