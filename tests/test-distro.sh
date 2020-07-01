#!/usr/bin/env bash

if echo "$*" | grep -q -- 'help'; then
    prog=$(basename -s.wrapper "$0")
    echo "Usage: $prog LXC-IMAGE ORIGINAL-CHANNEL UPGRADE-WITH-CHANNEL [PROXY]"
    echo ""
    echo "Example: $prog ubuntu:18.04 latest/beta latest/edge"
    echo "Use Ubuntu 18.04 for running our tests."
    echo "We test that microk8s from latest/edge (UPGRADE-WITH-CHANNEL) runs fine."
    echo "We test that microk8s from latest/beta (ORIGINAL-CHANNEL) can be upgraded"
    echo "to the revision that is currently on latest/edge (UPGRADE-WITH-CHANNEL)."
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

  # Allow for the machine to boot and get an IP
  sleep 20
  tar cf - ./tests | lxc exec $NAME -- tar xvf - -C /var/tmp
  DISTRO_DEPS="${DISTRO//:/_}"
  lxc exec $NAME -- /bin/bash "/var/tmp/tests/lxc/install-deps/$DISTRO_DEPS"
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

# Test addons upgrade
# TODO Handle local in the upgrade
create_machine $NAME $PROXY
# use 'script' for required tty: https://github.com/lxc/lxd/issues/1724#issuecomment-194416774
lxc exec $NAME -- script -e -c "UPGRADE_MICROK8S_FROM=${FROM_CHANNEL} UPGRADE_MICROK8S_TO=${TO_CHANNEL} pytest -s /var/tmp/tests/test-upgrade.py"
lxc delete $NAME --force

# Test addons
NAME=machine-$RANDOM
create_machine $NAME $PROXY
if [ ${TO_CHANNEL} == "local" ]
then
  lxc file push ./microk8s_latest_amd64.snap $VM2_NAME/tmp/
  lxc exec $VM1_NAME -- snap install /tmp/microk8s_latest_amd64.snap --dangerous --classic
else
  lxc exec $NAME -- snap install microk8s --channel=${TO_CHANNEL} --classic
fi
lxc exec $NAME -- /var/tmp/tests/patch-kube-proxy.sh
# use 'script' for required tty: https://github.com/lxc/lxd/issues/1724#issuecomment-194416774
lxc exec $NAME -- script -e -c "pytest -s /var/tmp/tests/test-addons.py"
lxc exec $NAME -- microk8s reset
lxc delete $NAME --force
