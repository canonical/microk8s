#!/usr/bin/env bash

function setup_addons_upgrade() {
  export NAME=machine-$RANDOM
  create_machine $NAME $PROXY
}

function test_addons_upgrade() {
  # use 'script' for required tty: https://github.com/lxc/lxd/issues/1724#issuecomment-194416774
  lxc exec $NAME -- script -e -c "UPGRADE_MICROK8S_FROM=${FROM_CHANNEL} UPGRADE_MICROK8S_TO=${TO_CHANNEL} pytest -s /root/tests/test-upgrade.py"
} 

function post_addons_upgrade() {
  lxc delete $NAME --force
}