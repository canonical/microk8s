#!/usr/bin/env bash

function setup_upgrade_path() {
  # Test upgrade-path
  export NAME=machine-$RANDOM
  create_machine $NAME $PROXY
}

function test_upgrade_path() {
  # use 'script' for required tty: https://github.com/lxc/lxd/issues/1724#issuecomment-194416774
  if [[ ${TO_CHANNEL} =~ /.*/microk8s.*snap ]]
  then
    lxc file push ${TO_CHANNEL} $NAME/tmp/microk8s_latest_amd64.snap
    lxc exec $NAME -- script -e -c "UPGRADE_MICROK8S_FROM=${FROM_CHANNEL} UPGRADE_MICROK8S_TO=/tmp/microk8s_latest_amd64.snap pytest -s /root/tests/test-upgrade-path.py"
  else
    lxc exec $NAME -- script -e -c "UPGRADE_MICROK8S_FROM=${FROM_CHANNEL} UPGRADE_MICROK8S_TO=${TO_CHANNEL} pytest -s /root/tests/test-upgrade-path.py"
  fi
}

function post_upgrade_path() {
  lxc delete $NAME --force
}
