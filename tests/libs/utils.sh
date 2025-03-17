#!/usr/bin/env bash

function create_machine() {
  local NAME=$1
  local DISTRO=$2
  local PROXY=$3
  if ! lxc profile show microk8s
  then
    lxc profile copy default microk8s
  fi
  lxc profile edit microk8s < tests/lxc/microk8s.profile

  lxc launch -p default -p microk8s "$DISTRO" "$NAME"

  # Allow for the machine to boot and get an IP
  timeout 60 bash -c 'until lxc list "$NAME" -c4 | grep -q eth; do sleep 5; done' || { echo "Error: $NAME did not get an IP within 60s"; exit 1; }

  tar cf - ./tests | lxc exec "$NAME" -- tar xvf - -C /root
  DISTRO_DEPS_TMP="${DISTRO//:/_}"
  DISTRO_DEPS="${DISTRO_DEPS_TMP////-}"
  lxc exec "$NAME" -- /bin/bash "/root/tests/lxc/install-deps/$DISTRO_DEPS"
  lxc exec "$NAME" -- reboot
  timeout 60 bash -c 'until lxc exec "$NAME" -- /bin/true; do sleep 5; done' || { echo "Error: Con
tainer $NAME did not become ready in 60s"; exit 1; }

  trap 'lxc delete '"${NAME}"' --force || true' EXIT
  if [ "$#" -ne 1 ]
  then
    lxc exec "$NAME" -- /bin/bash -c "echo HTTPS_PROXY=$PROXY >> /etc/environment"
    lxc exec "$NAME" -- /bin/bash -c "echo https_proxy=$PROXY >> /etc/environment"
    lxc exec "$NAME" -- reboot
    timeout 60 bash -c 'until lxc exec "$NAME" -- /bin/true; do sleep 5; done' || { echo "Error: Con
tainer $NAME did not become ready in 60s after applying proxy settings"; exit 1; }
  fi
}

function setup_tests() {
  DISTRO="${1-$DISTRO}"
  FROM_CHANNEL="${2-$FROM_CHANNEL}"
  TO_CHANNEL="${3-$TO_CHANNEL}"
  PROXY="${4-$PROXY}"

  export DEBIAN_FRONTEND=noninteractive
  apt-get install python3-pip -y
  pip3 install -U pytest requests pyyaml sh
  apt-get install jq -y
  snap install kubectl --classic
  export ARCH=$(uname -m)
  export LXC_PROFILE="tests/lxc/microk8s.profile"
  export BACKEND="lxc"
  export CHANNEL_TO_TEST=${TO_CHANNEL}
}
