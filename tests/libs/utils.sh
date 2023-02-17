#!/usr/bin/env bash

function create_machine() {
  local NAME=$1
  if ! lxc profile show microk8s
  then
    lxc profile copy default microk8s
  fi
  cat tests/lxc/microk8s.profile | lxc profile edit microk8s

  lxc launch -p default -p microk8s $DISTRO $NAME

  # Allow for the machine to boot and get an IP
  sleep 20
  tar cf - ./tests | lxc exec $NAME -- tar xvf - -C /root
  DISTRO_DEPS_TMP="${DISTRO//:/_}"
  DISTRO_DEPS="${DISTRO_DEPS_TMP////-}"
  lxc exec $NAME -- /bin/bash "/root/tests/lxc/install-deps/$DISTRO_DEPS"
  lxc exec $NAME -- reboot
  sleep 20

  trap "lxc delete ${NAME} --force || true" EXIT
  if [ "$#" -ne 1 ]
  then
    lxc exec $NAME -- /bin/bash -c "echo HTTPS_PROXY=$2 >> /etc/environment"
    lxc exec $NAME -- /bin/bash -c "echo https_proxy=$2 >> /etc/environment"
    lxc exec $NAME -- reboot
    sleep 20
  fi
}

function setup_tests() {
  export DISTRO=$1
  export FROM_CHANNEL=$2
  export TO_CHANNEL=$3
  export PROXY=""
  if [ "$#" -ne 3 ]
  then
    export PROXY=$4
  fi

  apt-get install python3-pip -y
  pip3 install -U pytest requests pyyaml sh
  # apt-get install awscli -y
  apt-get install jq -y
  snap install kubectl --classic
  export ARCH=$(uname -m)
  export LXC_PROFILE="tests/lxc/microk8s.profile"
  export BACKEND="lxc"
  export CHANNEL_TO_TEST=${TO_CHANNEL}
}