#!/usr/bin/env bash

source tests/libs/utils.sh

airgap_wait_for_pods() {
  container="$1"

  lxc exec "$container" -- bash -c "
    while ! microk8s kubectl wait -n kube-system ds/calico-node --for=jsonpath='{.status.numberReady}'=1; do
      echo waiting for calico
      sleep 3
    done

    while ! microk8s kubectl wait -n kube-system deploy/hostpath-provisioner --for=jsonpath='{.status.readyReplicas}'=1; do
      echo waiting for hostpath provisioner
      sleep 3
    done

    while ! microk8s kubectl wait -n kube-system deploy/coredns --for=jsonpath='{.status.readyReplicas}'=1; do
      echo waiting for coredns
      sleep 3
    done
  "
}

function setup_airgap_registry_mirror() {
  local NAME=$1
  local DISTRO=$2
  local PROXY=$3
  local TO_CHANNEL=$4

  create_machine "$NAME" "$DISTRO" "$PROXY"
  if [[ ${TO_CHANNEL} =~ /.*/microk8s.*snap ]]
  then
    lxc file push "${TO_CHANNEL}" "$NAME"/tmp/microk8s_latest_amd64.snap
    lxc exec "$NAME" -- snap install /tmp/microk8s_latest_amd64.snap --dangerous --classic
  else
    lxc exec "$NAME" -- snap install microk8s --channel="${TO_CHANNEL}" --classic
  fi
}

function setup_airgap_registry_addons() {
  local NAME=$1
  lxc exec "$NAME" -- microk8s enable registry storage dns
}

function wait_airgap_registry() {
  local NAME=$1
  airgap_wait_for_pods "$NAME"
  lxc exec "$NAME" -- bash -c '
    while ! curl --silent 127.0.0.1:32000/v2/_catalog; do
      echo waiting for registry
      sleep 2
    done
  '
}

function push_images_to_registry() {
  local NAME=$1
  lxc exec "$NAME" -- bash -c '
    for image in $(microk8s ctr image ls -q | grep -v "sha256:"); do
      mirror=$(echo $image | sed '"'s,\(docker.io\|k8s.gcr.io\|registry.k8s.io\|quay.io\),${NAME}:32000,g'"')
      sudo microk8s ctr image convert ${image} ${mirror}
      sudo microk8s ctr image push ${mirror} --plain-http
    done
  '
}

function setup_airgapped_microk8s() {
  local NAME=$1
  local DISTRO=$2
  local PROXY=$3
  local TO_CHANNEL=$4

  create_machine "$NAME" "$DISTRO" "$PROXY"
  if [[ ${TO_CHANNEL} =~ /.*/microk8s.*snap ]]
  then
    lxc file push "${TO_CHANNEL}" "$NAME"/tmp/microk8s.snap
  else
    lxc exec "$NAME" -- snap download microk8s --channel="${TO_CHANNEL}" --target-directory /tmp --basename microk8s
  fi
  lxc exec "$NAME" -- bash -c "
    snap install core20
    snap install snapd
    echo '
  network:
    version: 2
    ethernets:
      eth0:
        dhcp4-overrides: { use-routes: false }
        routes: [{ to: 0.0.0.0/0, scope: link }]
  ' > /etc/netplan/70-airgap.yaml
    netplan apply
  "
  if lxc exec "$NAME" -- bash -c "ping -c1 1.1.1.1"; then
    echo "machine for airgap test has internet access when it should not"
    exit 1
  fi
  lxc exec "$NAME" -- snap install /tmp/microk8s.snap --dangerous --classic
}

function configure_airgapped_microk8s_mirrors() {
  local REGISTRY_NAME=$1
  local AIRGAPPED_NAME=$2
  lxc exec "$AIRGAPPED_NAME" -- bash -c '
    echo "
      server = \"http://'"${REGISTRY_NAME}"':32000\"

      [host.\"http://'"${REGISTRY_NAME}"':32000\"]
        capabilities = [\"pull\", \"resolve\"]
    " > hosts.toml

    for registry in registry.k8s.io k8s.gcr.io docker.io quay.io; do
      mkdir -p /var/snap/microk8s/current/args/certs.d/$registry
      cp hosts.toml /var/snap/microk8s/current/args/certs.d/$registry/hosts.toml
    done

    sudo snap restart microk8s.daemon-containerd
  '
}

function test_airgapped_microk8s() {
  local NAME=$1
  lxc exec "$NAME" -- bash -c 'sudo microk8s enable hostpath-storage dns'
  airgap_wait_for_pods "$NAME"
}

function post_airgap_tests() {
  local REGISTRY_NAME=$1
  local AIRGAPPED_NAME=$2
  lxc rm "$REGISTRY_NAME" --force
  lxc rm "$AIRGAPPED_NAME" --force
}

TEMP=$(getopt -o "lh" \
              --long help,lib-mode,registry-name:,node-name:,distro:,channel:,proxy: \
              -n "$(basename "$0")" -- "$@")

if [ $? != 0 ] ; then echo "Terminating..." >&2 ; exit 1 ; fi

eval set -- "$TEMP"

REGISTRY_NAME="${REGISTRY_NAME-"registry-$RANDOM"}"
AIRGAPPED_NAME="${AIRGAPPED_NAME-"machine-$RANDOM"}"
DISTRO="${DISTRO-}"
TO_CHANNEL="${TO_CHANNEL-}"
PROXY="${PROXY-}"
LIBRARY_MODE=false

while true; do
  case "$1" in
    -l | --lib-mode ) LIBRARY_MODE=true; shift ;;
    --registry-name ) REGISTRY_NAME="$2"; shift 2 ;;
    --node-name ) AIRGAPPED_NAME="$2"; shift 2 ;;
    --distro ) DISTRO="$2"; shift 2 ;;
    --channel ) TO_CHANNEL="$2"; shift 2 ;;
    --proxy ) PROXY="$2"; shift 2 ;;
    -h | --help ) 
      prog=$(basename -s.wrapper "$0")
      echo "Usage: $prog [options...]"
      echo "     --registry-name <name> Name to be used for registry LXD containers"
      echo "         Can also be set by using REGISTRY_NAME environment variable"
      echo "     --node-name <name> Name to be used for LXD containers"
      echo "         Can also be set by using AIRGAPPED_NAME environment variable"
      echo "     --distro <distro> Distro image to be used for LXD containers Eg. ubuntu:18.04"
      echo "         Can also be set by using DISTRO environment variable"
      echo "     --channel <channel> Channel to be tested Eg. latest/edge"
      echo "         Can also be set by using TO_CHANNEL environment variable"
      echo "     --proxy <url> Proxy url to be used by the nodes"
      echo "         Can also be set by using PROXY environment variable"
      echo " -l, --lib-mode Make the script act like a library Eg. true / false"
      echo
      exit ;;
    -- ) shift; break ;;
    * ) break ;;
  esac
done

if [ "$LIBRARY_MODE" == "false" ];
then
  echo "1/7 -- Install registry mirror"
  setup_airgap_registry_mirror "$REGISTRY_NAME" "$DISTRO" "$PROXY" "$TO_CHANNEL"
  echo "2/7 -- Install MicroK8s addons"
  setup_airgap_registry_addons "$REGISTRY_NAME"
  echo "3/7 -- Wait for MicroK8s instance to come up"
  wait_airgap_registry "$REGISTRY_NAME"
  echo "4/7 -- Push images to registry mirror"
  push_images_to_registry "$REGISTRY_NAME"
  echo "5/7 -- Install MicroK8s on an airgap environment"
  setup_airgapped_microk8s "$AIRGAPPED_NAME" "$DISTRO" "$PROXY" "$TO_CHANNEL"
  echo "6/7 -- Configure MicroK8s registry mirrors"
  configure_airgapped_microk8s_mirrors "$REGISTRY_NAME" "$AIRGAPPED_NAME"
  echo "7/7 -- Wait for airgap MicroK8s to come up"
  test_airgapped_microk8s "$AIRGAPPED_NAME"
  echo "Cleaning up"
  post_airgap_tests "$REGISTRY_NAME" "$AIRGAPPED_NAME"
fi