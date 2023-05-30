#!/usr/bin/env bash

source tests/libs/utils.sh

function airgap_wait_for_pods() {
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

  lxc exec "$NAME" -- bash -c "
    mkdir -p /root/snap/microk8s/common
    echo '
---
version: 0.1.0
# pre-configure DNS args to save time from unnecessary kubelet restarts
extraKubeletArgs:
  --cluster-dns: 10.152.183.10
  --cluster-domain: cluster.local
addons:
  - name: dns
  - name: storage
  - name: registry
' > /root/snap/microk8s/common/.microk8s.yaml
  "

  if [[ ${TO_CHANNEL} =~ /.*/microk8s.*snap ]]
  then
    lxc file push "${TO_CHANNEL}" "$NAME"/var/tmp/microk8s_latest_amd64.snap
    while ! lxc exec "$NAME" -- bash -c "snap install snapd"; do
      echo retry install snapd
      sleep 1
    done
    while ! lxc exec "$NAME" -- bash -c "snap install core20"; do
      echo retry install core20
      sleep 1
    done
    while ! lxc exec "$NAME" -- bash -c "snap install /var/tmp/microk8s_latest_amd64.snap --dangerous --classic"; do
      echo retry snap install
      sleep 1
    done
  else
    lxc exec "$NAME" -- snap install microk8s --channel="${TO_CHANNEL}" --classic
  fi
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
      mirror=$(echo $image | sed '"'s,\(docker.io\|k8s.gcr.io\|registry.k8s.io\|quay.io\|public.ecr.aws\),${NAME}:32000,g'"')
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
    lxc file push "${TO_CHANNEL}" "$NAME"/var/tmp/microk8s.snap
  else
    lxc exec "$NAME" -- snap download microk8s --channel="${TO_CHANNEL}" --target-directory /var/tmp --basename microk8s
  fi
  while ! lxc exec "$NAME" -- bash -c "snap install snapd"; do
    echo retry install snapd
    sleep 1
  done
  while ! lxc exec "$NAME" -- bash -c "snap install core20"; do
    echo retry install core20
    sleep 1
  done

  lxc exec "$NAME" -- bash -c "
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
  lxc exec "$NAME" -- bash -c '
  mkdir -p /root/snap/microk8s/common
  echo "
---
version: 0.1.0
# pre-configure DNS args to save time from unnecessary kubelet restarts
extraKubeletArgs:
  --cluster-dns: 10.152.183.10
  --cluster-domain: cluster.local
containerdRegistryConfigs:
  docker.io: |
    [host.\"http://'"${REGISTRY_NAME}"':32000\"]
      capabilities = [\"pull\", \"resolve\"]
  registry.k8s.io: |
    [host.\"http://'"${REGISTRY_NAME}"':32000\"]
      capabilities = [\"pull\", \"resolve\"]
  quay.io: |
    [host.\"http://'"${REGISTRY_NAME}"':32000\"]
      capabilities = [\"pull\", \"resolve\"]
  k8s.gcr.io: |
    [host.\"http://'"${REGISTRY_NAME}"':32000\"]
      capabilities = [\"pull\", \"resolve\"]
  public.ecr.aws: |
    [host.\"http://'"${REGISTRY_NAME}"':32000\"]
      capabilities = [\"pull\", \"resolve\"]
addons:
  - name: dns
  - name: storage
  - name: registry
  " > /root/snap/microk8s/common/.microk8s.yaml

  while ! snap install /var/tmp/microk8s.snap --dangerous --classic; do
    sleep 1
  done
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

REGISTRY_NAME="${REGISTRY_NAME:-"registry-$RANDOM"}"
AIRGAPPED_NAME="${AIRGAPPED_NAME:-"machine-$RANDOM"}"
DISTRO="${DISTRO:-}"
TO_CHANNEL="${TO_CHANNEL:-}"
PROXY="${PROXY:-}"
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
  echo "1/5 -- Install registry mirror"
  setup_airgap_registry_mirror "$REGISTRY_NAME" "$DISTRO" "$PROXY" "$TO_CHANNEL"
  echo "2/5 -- Wait for MicroK8s instance with registry to come up"
  wait_airgap_registry "$REGISTRY_NAME"
  echo "3/5 -- Push images to registry mirror"
  push_images_to_registry "$REGISTRY_NAME"
  echo "4/5 -- Install MicroK8s on an airgap environment (using registry mirror)"
  setup_airgapped_microk8s "$AIRGAPPED_NAME" "$DISTRO" "$PROXY" "$TO_CHANNEL"
  echo "5/5 -- Wait for airgapped MicroK8s to come up"
  airgap_wait_for_pods "$AIRGAPPED_NAME"
  echo "Cleaning up"
  post_airgap_tests "$REGISTRY_NAME" "$AIRGAPPED_NAME"
fi
