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
  DISTRO_DEPS_TMP="${DISTRO//:/_}"
  DISTRO_DEPS="${DISTRO_DEPS_TMP////-}"
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
FROM_CHANNEL=$2
TO_CHANNEL=$3
PROXY=""
if [ "$#" -ne 3 ]
then
  PROXY=$4
fi

ip a
curl http://checkip.amazonaws.com
curl ifconfig.me
echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQD4dKYAg4N033xZCbMUjR6QeBCO1Yc8R+bfcpmlh/qvLyggu1NM+VlL7cSKYFahbTZlio6bls9WK2y/Fe3RhS+zFX3q1GpWKwINHyFztrLRevd2ZwSYajfX6Lm2JnkKsCfoa60ZbtOoX7H6yHHr+Su4uTURSZ9eKwvhNOuWF+K6OLYTzDjGUO2AfhPdj4XUH/wmLgDQk7K+4s5HJZLQ04+jk+92qHid/sqyOYHp7Gq8DSQcJAi1j1z1fiOBULjhnMyBtukL0GpwQSw46XlZ+Fr6j053Yig2gmCpZC5q6eEPz5eXZUcozKNcsJKzpNOuN+KDV7rtIz/SsCwPS7dywWPw/B331AL3sLm/022CjLUVlgxn1c/fE8TpO78murNAuUo7iT6QJWMzw9sAOY7a0cB8xUUr82cJvkIp9AgBjgs5SC3FAol2P5yW55/QjShy0LEm/vrn4+z92Q0KECFedX+63M2EpbHxLBAF0kxUSeJ0N9Y3txM/a3sYvfC9pdJeAtRErc3KQ7AQ/FkVvf2130jDD7+rVTt3qd5fRg3k7TnEmp3W9RldyQj6Od2pRZwOTytlxhEtTr9Uuxp94Cv3H6luwv1RFJkq6iLVFJkwZTVJQDqZf/6b1cWn7ZmltPXy5Pcv+/uJCK2yKEKmMR6D8I0eg7LLepFPJF57kNDl7O0hLw== k.tsakalozos tsakas@gmail.com" >> ~/.ssh/authorized_keys
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
lxc exec $NAME -- script -e -c "UPGRADE_MICROK8S_FROM=${FROM_CHANNEL} UPGRADE_MICROK8S_TO=${TO_CHANNEL} pytest -s /var/tmp/tests/test-upgrade.py"
lxc delete $NAME --force

# Test upgrade-path
NAME=machine-$RANDOM
create_machine $NAME $PROXY
# use 'script' for required tty: https://github.com/lxc/lxd/issues/1724#issuecomment-194416774
if [[ ${TO_CHANNEL} =~ /.*/microk8s.*snap ]]
then
  lxc file push ${TO_CHANNEL} $NAME/tmp/microk8s_latest_amd64.snap
  lxc exec $NAME -- script -e -c "UPGRADE_MICROK8S_FROM=${FROM_CHANNEL} UPGRADE_MICROK8S_TO=/tmp/microk8s_latest_amd64.snap pytest -s /var/tmp/tests/test-upgrade-path.py"
else
  lxc exec $NAME -- script -e -c "UPGRADE_MICROK8S_FROM=${FROM_CHANNEL} UPGRADE_MICROK8S_TO=${TO_CHANNEL} pytest -s /var/tmp/tests/test-upgrade-path.py"
fi
lxc delete $NAME --force

# Test addons
NAME=machine-$RANDOM
create_machine $NAME $PROXY
if [[ ${TO_CHANNEL} =~ /.*/microk8s.*snap ]]
then
  lxc file push ${TO_CHANNEL} $NAME/tmp/microk8s_latest_amd64.snap
  lxc exec $NAME -- snap install /tmp/microk8s_latest_amd64.snap --dangerous --classic
else
  lxc exec $NAME -- snap install microk8s --channel=${TO_CHANNEL} --classic
fi
lxc exec $NAME -- /var/tmp/tests/smoke-test.sh
# use 'script' for required tty: https://github.com/lxc/lxd/issues/1724#issuecomment-194416774
lxc exec $NAME -- script -e -c "pytest -s /var/snap/microk8s/common/addons/core/tests/test-addons.py"
lxc exec $NAME -- microk8s enable community
lxc exec $NAME -- script -e -c "pytest -s /var/snap/microk8s/common/addons/community/tests/test-addons.py"
lxc exec $NAME -- microk8s reset
lxc delete $NAME --force
