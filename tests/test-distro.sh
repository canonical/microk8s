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
FROM_CHANNEL=$2
TO_CHANNEL=$3
PROXY=""
if [ "$#" -ne 3 ]
then
  PROXY=$4
fi

# Test airgap installation.
# DISABLE_AIRGAP_TESTS=1 can be set to disable them.
DISABLE_AIRGAP_TESTS="${DISABLE_AIRGAP_TESTS:-0}"
if [ "x${DISABLE_AIRGAP_TESTS}" != "x1" ]; then
  . tests/test-airgap.sh
fi

# Test clustering. This test will create lxc containers or multipass VMs
# therefore we do not need to run it inside a VM/container
apt-get install python3-pip -y
pip3 install -U pytest requests pyyaml sh
export LXC_PROFILE="tests/lxc/microk8s.profile"
export BACKEND="lxc"
export CHANNEL_TO_TEST=${TO_CHANNEL}
TRY_ATTEMPT=0
while ! (timeout 3600 pytest -s tests/test-cluster.py) &&
      ! [ ${TRY_ATTEMPT} -eq 3 ]
do
  TRY_ATTEMPT=$((TRY_ATTEMPT+1))
  sleep 1
done
if [ ${TRY_ATTEMPT} -eq 3 ]
then
  echo "Test clusterring took longer than expected"
  exit 1
fi

# Test addons upgrade
NAME=machine-$RANDOM
create_machine $NAME $PROXY
# use 'script' for required tty: https://github.com/lxc/lxd/issues/1724#issuecomment-194416774
lxc exec $NAME -- script -e -c "UPGRADE_MICROK8S_FROM=${FROM_CHANNEL} UPGRADE_MICROK8S_TO=${TO_CHANNEL} pytest -s /root/tests/test-upgrade.py"
lxc delete $NAME --force

# Test upgrade-path
NAME=machine-$RANDOM
create_machine $NAME $PROXY
# use 'script' for required tty: https://github.com/lxc/lxd/issues/1724#issuecomment-194416774
if [[ ${TO_CHANNEL} =~ /.*/microk8s.*snap ]]
then
  lxc file push ${TO_CHANNEL} $NAME/tmp/microk8s_latest_amd64.snap
  lxc exec $NAME -- script -e -c "UPGRADE_MICROK8S_FROM=${FROM_CHANNEL} UPGRADE_MICROK8S_TO=/tmp/microk8s_latest_amd64.snap pytest -s /root/tests/test-upgrade-path.py"
else
  lxc exec $NAME -- script -e -c "UPGRADE_MICROK8S_FROM=${FROM_CHANNEL} UPGRADE_MICROK8S_TO=${TO_CHANNEL} pytest -s /root/tests/test-upgrade-path.py"
fi
lxc delete $NAME --force

# Test addons
NAME=machine-$RANDOM
create_machine $NAME $PROXY
if [[ ${TO_CHANNEL} =~ /.*/microk8s.*snap ]]
then
  lxc file push ${TO_CHANNEL} $NAME/tmp/microk8s_latest_amd64.snap
  lxc exec $NAME -- snap install /tmp/microk8s_latest_amd64.snap --dangerous --classic
  lxc exec $NAME -- bash -c '/root/tests/connect-all-interfaces.sh'
else
  lxc exec $NAME -- snap install microk8s --channel=${TO_CHANNEL}
fi
lxc exec $NAME -- /root/tests/smoke-test.sh
# use 'script' for required tty: https://github.com/lxc/lxd/issues/1724#issuecomment-194416774
lxc exec $NAME -- script -e -c "STRICT=\"yes\" pytest -s /var/snap/microk8s/common/addons/core/tests/test-addons.py"
lxc exec $NAME -- microk8s enable community
lxc exec $NAME -- script -e -c "STRICT=\"yes\" pytest -s /var/snap/microk8s/common/addons/community/tests/test-addons.py"
lxc exec $NAME -- microk8s reset
lxc delete $NAME --force
