#!/usr/bin/env bash

if echo "$*" | grep -q -- 'help'; then
    prog=$(basename -s.wrapper "$0")
    echo "Usage: $prog LXC-IMAGE ORIGINAL-CHANNEL UPGRADE-WITH-CHANNEL [PROXY]"
    echo ""
    echo "Example: $prog ubuntu:18.04 beta edge"
    echo "Use Ubuntu 18.04 for running our tests."
    echo "We test that microk8s from edge (UPGRADE-WITH-CHANNEL) runs fine."
    echo "We test that microk8s from beta (ORIGINAL-CHANNEL) can be upgraded"
    echo "to the revision that is currently on edge (UPGRADE-WITH-CHANNEL)."
    echo
    exit
fi

function create_machine() {
  local NAME=$1
  if ! lxc profile show microk8s
  then
    lxc profile copy default microk8s
  fi
  cat tests/lxc/microk8s.profile | lxc profile edit microk8s

  lxc launch -p default -p microk8s $DISTRO $NAME
  trap "lxc delete ${NAME} --force || true" EXIT
  if [ "$#" -ne 1 ]
  then
    lxc exec $NAME -- /bin/bash -c "echo HTTPS_PROXY=$2 >> /etc/environment"
    lxc exec $NAME -- /bin/bash -c "echo https_proxy=$2 >> /etc/environment"
    lxc exec $NAME -- reboot
    sleep 20
  fi

  # Allow for the machine to boot and get an IP
  sleep 20
  tar cf - ./tests | lxc exec $NAME -- tar xvf - -C /var/tmp
  lxc exec $NAME -- /bin/bash "/var/tmp/tests/lxc/install-deps/$DISTRO"
  lxc exec $NAME -- reboot
  sleep 20
}

set -uex

DISTRO=$1
NAME=machine-$RANDOM
FROM_CHANNEL=$2
TO_CHANNEL=$3
PROXY=""
if [ "$#" -ne 3 ]
then
  PROXY=$4
fi

create_machine $NAME $PROXY
lxc exec $NAME -- snap install microk8s --channel=${TO_CHANNEL} --classic
lxc exec $NAME -- /var/tmp/tests/patch-kube-proxy.sh
# use 'script' for required tty: https://github.com/lxc/lxd/issues/1724#issuecomment-194416774
lxc exec $NAME -- script -e -c "pytest -s /var/tmp/tests/test-addons.py"
lxc exec $NAME -- microk8s.reset
lxc delete $NAME --force

NAME=machine-$RANDOM
create_machine $NAME $PROXY
# use 'script' for required tty: https://github.com/lxc/lxd/issues/1724#issuecomment-194416774
lxc exec $NAME -- script -e -c "UPGRADE_MICROK8S_FROM=${FROM_CHANNEL} UPGRADE_MICROK8S_TO=${TO_CHANNEL} pytest -s /var/tmp/tests/test-upgrade.py"
lxc delete $NAME --force
