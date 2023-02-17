#!/usr/bin/env bash

function setup_test_addons() {
  if [[ ${TO_CHANNEL} =~ /.*/microk8s.*snap ]]
  then
    snap install ${TO_CHANNEL} --dangerous --classic
  else
    snap install microk8s --channel=${TO_CHANNEL} --classic
  fi

  microk8s status --wait-ready

  export NAME=machine-$RANDOM
  create_machine $NAME $PROXY
  if [[ ${TO_CHANNEL} =~ /.*/microk8s.*snap ]]
  then
    lxc file push ${TO_CHANNEL} $NAME/tmp/microk8s_latest_amd64.snap
    lxc exec $NAME -- snap install /tmp/microk8s_latest_amd64.snap --dangerous --classic
  else
    lxc exec $NAME -- snap install microk8s --channel=${TO_CHANNEL} --classic
  fi
}

function test_smoke() {
  lxc exec $NAME -- /root/tests/smoke-test.sh
}

function test_core_addons() {
  # use 'script' for required tty: https://github.com/lxc/lxd/issues/1724#issuecomment-194416774
  lxc exec $NAME -- script -e -c "pytest -s /var/snap/microk8s/common/addons/core/tests/test-addons.py"
}

function test_community_addons() {
  lxc exec $NAME -- microk8s enable community
  lxc exec $NAME -- script -e -c "pytest -s /var/snap/microk8s/common/addons/community/tests/"
}

function test_eksd_addons() {
  if [ -d "/var/snap/microk8s/common/addons/eksd" ]
  then
    if [ -f "/var/snap/microk8s/common/addons/eksd/tests/test-addons.sh" ]; then
      . /var/snap/microk8s/common/addons/eksd/tests/test-addons.sh
    fi
  fi
}

function test_gpu_addon() {
  if [ -f "/var/snap/microk8s/common/addons/core/tests/test-addons.py" ] &&
   grep test_gpu /var/snap/microk8s/common/addons/core/tests/test-addons.py -q
  then
    timeout 3600 pytest -s /var/snap/microk8s/common/addons/core/tests/test-addons.py -k test_gpu
  fi
}

function post_test_addons() {
  lxc exec $NAME -- microk8s reset
  lxc delete $NAME --force
}
