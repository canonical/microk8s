#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Istio"

if [ ! -f "${SNAP_DATA}/bin/istioctl" ]
then
  ISTIO_VERSION="v1.5.7"
  echo "Fetching istioctl version $ISTIO_VERSION."
  ISTIO_ERSION=$(echo $ISTIO_VERSION | sed 's/v//g')
  mkdir -p "${SNAP_DATA}/tmp/istio"
  (cd "${SNAP_DATA}/tmp/istio"
  curl -Lk https://github.com/istio/istio/releases/download/${ISTIO_ERSION}/istio-${ISTIO_ERSION}-linux.tar.gz -o "$SNAP_DATA/tmp/istio/istio.tar.gz"
  gzip -d "$SNAP_DATA/tmp/istio/istio.tar.gz"
  tar -xvf "$SNAP_DATA/tmp/istio/istio.tar"
  chmod 777 "$SNAP_DATA/tmp/istio/istio-${ISTIO_ERSION}")
  mkdir -p "$SNAP_DATA/bin/"
  mv "$SNAP_DATA/tmp/istio/istio-${ISTIO_ERSION}/bin/istioctl" "$SNAP_DATA/bin/"
  chmod +x "$SNAP_DATA/bin/"

  mkdir -p "$SNAP_DATA/actions/istio/"

  cp "$SNAP_DATA/tmp/istio/istio-${ISTIO_ERSION}"/install/kubernetes/helm/istio-init/files/crd*.yaml "$SNAP_DATA/actions/istio/"
  mv "$SNAP_DATA/tmp/istio/istio-${ISTIO_ERSION}/install/kubernetes/istio-demo.yaml" "$SNAP_DATA/actions/istio/"

  rm -rf "$SNAP_DATA/tmp/istio"
fi

# pod/servicegraph will start failing without dns
"$SNAP/microk8s-enable.wrapper" dns


KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
for i in "${SNAP_DATA}"/actions/istio/crd*yaml
do
  $KUBECTL apply -f "$i"
done

$KUBECTL apply -f "${SNAP_DATA}/actions/istio/istio-demo.yaml"
touch "$SNAP_USER_COMMON/istio.lock"

refresh_opt_in_config "allow-privileged" "true" kube-apiserver
restart_service apiserver

echo "Istio is starting"
echo ""
echo "To configure mutual TLS authentication consult the Istio documentation."
