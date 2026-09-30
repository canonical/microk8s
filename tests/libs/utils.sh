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
  sleep 20
  # CentOS 8,9 variants(rocky, alma) don't ship with tar, such a dirty hack...
  lxc exec "$NAME" -- /bin/bash -c "yum install tar -y || true"
  tar cf - ./tests | lxc exec "$NAME" -- tar xvf - -C /root
  DISTRO_DEPS_TMP="${DISTRO//:/_}"
  DISTRO_DEPS="${DISTRO_DEPS_TMP////-}"
  lxc exec "$NAME" -- /bin/bash "/root/tests/lxc/install-deps/$DISTRO_DEPS"
  lxc exec "$NAME" -- reboot
  sleep 20

  trap 'lxc delete '"${NAME}"' --force || true' EXIT
  if [ ! -z "${PROXY}" ]
  then
    lxc exec "$NAME" -- /bin/bash -c "echo HTTPS_PROXY=$PROXY >> /etc/environment"
    lxc exec "$NAME" -- /bin/bash -c "echo https_proxy=$PROXY >> /etc/environment"
    lxc exec "$NAME" -- reboot
    sleep 20
  fi
}

function setup_tests() {
  DISTRO="${1-$DISTRO}"
  FROM_CHANNEL="${2-$FROM_CHANNEL}"
  TO_CHANNEL="${3-$TO_CHANNEL}"
  PROXY="${4-$PROXY}"

  export DEBIAN_FRONTEND=noninteractive
  apt-get install python3-pip -y
  pip3 install -U pytest requests pyyaml sh psutil
  apt-get install jq -y
  snap install kubectl --classic
  export ARCH=$(uname -m)
  export LXC_PROFILE="tests/lxc/microk8s.profile"
  export BACKEND="lxc"
  export CHANNEL_TO_TEST=${TO_CHANNEL}
  export STRICT="yes"
}
