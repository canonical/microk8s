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
  lxc config device override $NAME root size=50GB

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

# Test clustering. This test will create lxc containers or multipass VMs
# therefore we do not need to run it inside a VM/container
apt-get install python3-pip -y
pip3 install -U pytest requests pyyaml sh
LXC_PROFILE="tests/lxc/microk8s.profile" BACKEND="lxc" CHANNEL_TO_TEST=${TO_CHANNEL} pytest -s tests/test-cluster.py

# Test addons upgrade
# TODO Handle local in the upgrade
create_machine $NAME $PROXY
# use 'script' for required tty: https://github.com/lxc/lxd/issues/1724#issuecomment-194416774
lxc exec $NAME -- script -e -c "UPGRADE_MICROK8S_FROM=${FROM_CHANNEL} UPGRADE_MICROK8S_TO=${TO_CHANNEL} pytest -s /root/tests/test-upgrade.py"
lxc delete $NAME --force

# Test upgrade-path
NAME=machine-$RANDOM
create_machine $NAME $PROXY
# use 'script' for required tty: https://github.com/lxc/lxd/issues/1724#issuecomment-194416774
lxc exec $NAME -- script -e -c "UPGRADE_MICROK8S_FROM=${FROM_CHANNEL} UPGRADE_MICROK8S_TO=${TO_CHANNEL} pytest -s /root/tests/test-upgrade-path.py"
lxc delete $NAME --force

# Test addons
NAME=machine-$RANDOM
create_machine $NAME $PROXY
if [ $(echo "${TO_CHANNEL}" | grep ".snap") ]
then
  lxc file push ./${TO_CHANNEL} $NAME/tmp/
  lxc exec $NAME -- snap install /tmp/${TO_CHANNEL} --dangerous
  lxc exec $NAME -- bash -c 'for i in docker-privileged docker-support kubernetes-support k8s-journald k8s-kubelet k8s-kubeproxy dot-kube network network-bind network-control network-observe firewall-control process-control kernel-module-observe mount-observe hardware-observe system-observe dot-config-helm home-read-all log-observe login-session-observe home opengl; do snap connect microk8s:$i; done'
else
  lxc exec $NAME -- snap install microk8s --channel=${TO_CHANNEL}
fi
lxc exec $NAME -- /root/tests/smoke-test.sh
# use 'script' for required tty: https://github.com/lxc/lxd/issues/1724#issuecomment-194416774
lxc exec $NAME -- script -e -c "pytest -s /root/tests/test-addons.py"
lxc exec $NAME -- microk8s reset
lxc delete $NAME --force
