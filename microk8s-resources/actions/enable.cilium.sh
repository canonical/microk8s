#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh
CA_CERT=/snap/core/current/etc/ssl/certs/ca-certificates.crt

ARCH=$(arch)
if ! [ "${ARCH}" = "amd64" ]; then
  echo "Cilium is not available for ${ARCH}" >&2
  exit 1
fi

"$SNAP/microk8s-enable.wrapper" helm3

echo "Restarting kube-apiserver"
refresh_opt_in_config "allow-privileged" "true" kube-apiserver
run_with_sudo preserve_env snapctl restart "${SNAP_NAME}.daemon-apiserver"

set_service_not_expected_to_start flanneld
run_with_sudo preserve_env snapctl stop "${SNAP_NAME}.daemon-flanneld"
remove_vxlan_interfaces

echo "Enabling Cilium"

read -ra CILIUM_VERSION <<< "$1"
if [ -z "$CILIUM_VERSION" ]; then
  CILIUM_VERSION="v1.6"
fi
CILIUM_ERSION=$(echo $CILIUM_VERSION | sed 's/v//g')

if [ -f "${SNAP_DATA}/bin/cilium-$CILIUM_ERSION" ]
then
  echo "Cilium version $CILIUM_VERSION is already installed."
else
  CILIUM_DIR="cilium-$CILIUM_ERSION"
  SOURCE_URI="https://github.com/cilium/cilium/archive"
  CILIUM_CNI_CONF="plugins/cilium-cni/05-cilium-cni.conf"
  CILIUM_LABELS="k8s-app=cilium"
  NAMESPACE=kube-system

  echo "Fetching cilium version $CILIUM_VERSION."
  run_with_sudo mkdir -p "${SNAP_DATA}/tmp/cilium"
  (cd "${SNAP_DATA}/tmp/cilium"
  run_with_sudo "${SNAP}/usr/bin/curl" --cacert $CA_CERT -L $SOURCE_URI/$CILIUM_VERSION.tar.gz -o "$SNAP_DATA/tmp/cilium/cilium.tar.gz"
  if ! run_with_sudo gzip -f -d "$SNAP_DATA/tmp/cilium/cilium.tar.gz"; then
    echo "Invalid version \"$CILIUM_VERSION\". Must be a branch on https://github.com/cilium/cilium."
    exit 1
  fi
  run_with_sudo tar -xf "$SNAP_DATA/tmp/cilium/cilium.tar" "$CILIUM_DIR/install" "$CILIUM_DIR/$CILIUM_CNI_CONF")

  run_with_sudo mv "$SNAP_DATA/args/cni-network/cni.conf" "$SNAP_DATA/args/cni-network/10-kubenet.conf" 2>/dev/null || true
  run_with_sudo mv "$SNAP_DATA/args/cni-network/flannel.conflist" "$SNAP_DATA/args/cni-network/20-flanneld.conflist" 2>/dev/null || true
  run_with_sudo cp "$SNAP_DATA/tmp/cilium/$CILIUM_DIR/$CILIUM_CNI_CONF" "$SNAP_DATA/args/cni-network/05-cilium-cni.conf"

  # Generate the YAMLs for Cilium and apply them
  (cd "${SNAP_DATA}/tmp/cilium/$CILIUM_DIR/install/kubernetes"
  ${SNAP_DATA}/bin/helm3 template cilium \
      --namespace $NAMESPACE \
      --set global.cni.confPath="$SNAP_DATA/args/cni-network" \
      --set global.cni.binPath="$SNAP_DATA/opt/cni/bin" \
      --set global.cni.customConf=true \
      --set global.containerRuntime.integration="containerd" \
      --set global.containerRuntime.socketPath="$SNAP_COMMON/run/containerd.sock" \
      | run_with_sudo tee cilium.yaml >/dev/null)

  run_with_sudo mkdir -p "$SNAP_DATA/actions/cilium/"
  run_with_sudo cp "$SNAP_DATA/tmp/cilium/$CILIUM_DIR/install/kubernetes/cilium.yaml" "$SNAP_DATA/actions/cilium.yaml"
  run_with_sudo sed -i 's;path: \(/var/run/cilium\);path: '"$SNAP_DATA"'\1;g' "$SNAP_DATA/actions/cilium.yaml"

  ${SNAP}/microk8s-status.wrapper --wait-ready >/dev/null
  echo "Deploying $SNAP_DATA/actions/cilium.yaml. This may take several minutes."
  "$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" apply -f "$SNAP_DATA/actions/cilium.yaml"
  "$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" -n $NAMESPACE rollout status ds/cilium

  # Fetch the Cilium CLI binary and install
  CILIUM_POD=$("$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" -n $NAMESPACE get pod -l $CILIUM_LABELS -o jsonpath="{.items[0].metadata.name}")
  CILIUM_BIN=$(mktemp)
  "$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" -n $NAMESPACE cp $CILIUM_POD:/usr/bin/cilium $CILIUM_BIN >/dev/null
  run_with_sudo mkdir -p "$SNAP_DATA/bin/"
  run_with_sudo mv $CILIUM_BIN "$SNAP_DATA/bin/cilium-$CILIUM_ERSION"
  run_with_sudo chmod +x "$SNAP_DATA/bin/"
  run_with_sudo chmod +x "$SNAP_DATA/bin/cilium-$CILIUM_ERSION"
  run_with_sudo ln -s $SNAP_DATA/bin/cilium-$CILIUM_ERSION $SNAP_DATA/bin/cilium

  run_with_sudo rm -rf "$SNAP_DATA/tmp/cilium"
fi

echo "Cilium is enabled"
