#!/usr/bin/env bash

function setup_addons_tests() {
  local NAME=$1
  local DISTRO=$2
  local PROXY=$3
  local TO_CHANNEL=$4

  create_machine "$NAME" "$DISTRO" "$PROXY"
  if [[ ${TO_CHANNEL} =~ /.*/microk8s.*snap ]]
  then
    lxc file push "${TO_CHANNEL}" "$NAME"/tmp/microk8s_latest_amd64.snap
    lxc exec "$NAME" -- snap install /tmp/microk8s_latest_amd64.snap --dangerous --classic
  else
    lxc exec "$NAME" -- snap install microk8s --channel="${TO_CHANNEL}" --classic
  fi
}

function run_smoke_test() {
  local NAME=$1
  lxc exec "$NAME" -- /root/tests/smoke-test.sh
  lxc exec "$NAME" -- script -e -c "pytest -s /root/tests/test-cluster-agent.py"
}

function run_core_addons_tests() {
  local NAME=$1
  # use 'script' for required tty: https://github.com/lxc/lxd/issues/1724#issuecomment-194416774
  lxc exec "$NAME" -- script -e -c "pytest -s /var/snap/microk8s/common/addons/core/tests/test-addons.py"
}

function run_community_addons_tests() {
  local NAME=$1
  lxc exec "$NAME" -- microk8s enable community
  lxc exec "$NAME" -- script -e -c "pytest -s /var/snap/microk8s/common/addons/community/tests/"
}

function run_gpu_addon_test() {
  if [ -f "/var/snap/microk8s/common/addons/core/tests/test-addons.py" ] &&
   grep test_gpu /var/snap/microk8s/common/addons/core/tests/test-addons.py -q
  then
    timeout 3600 pytest -s /var/snap/microk8s/common/addons/core/tests/test-addons.py -k test_gpu
  fi
}

function post_addons_tests() {
  local NAME=$1
  lxc exec "$NAME" -- microk8s reset
  lxc delete "$NAME" --force
}

TEMP=$(getopt -o "l,h" \
              --long help,lib-mode,node-name:,distro:,channel:,proxy: \
              -n "$(basename "$0")" -- "$@")

if [ $? != 0 ] ; then echo "Terminating..." >&2 ; exit 1 ; fi

eval set -- "$TEMP"

NAME="${NAME-"machine-$RANDOM"}"
DISTRO="${DISTRO-}"
TO_CHANNEL="${TO_CHANNEL-}"
PROXY="${PROXY-}"
LIBRARY_MODE=false

while true; do
  case "$1" in
    -l | --lib-mode ) LIBRARY_MODE=true; shift ;;
    --node-name ) NAME="$2"; shift 2 ;;
    --distro ) DISTRO="$2"; shift 2 ;;
    --channel ) TO_CHANNEL="$2"; shift 2 ;;
    --proxy ) PROXY="$2"; shift 2 ;;
    -h | --help )
      prog=$(basename -s.wrapper "$0")
      echo "Usage: $prog [options...]"
      echo "     --node-name <name> Name to be used for LXD containers"
      echo "         Can also be set by using NAME environment variable"
      echo "     --distro <distro> Distro image to be used for LXD containers Eg. ubuntu:18.04"
      echo "         Can also be set by using DISTRO environment variable"
      echo "     --channel <channel> Channel to be tested Eg. latest/edge"
      echo "         Can also be set by using TO_CHANNEL environment variable"
      echo "     --proxy <url> Proxy url to be used by the nodes"
      echo "         Can also be set by using PROXY environment variable"
      echo " -l, --lib-mode Make the script act like a library Eg. true / false"
      echo
      exit ;;
    -- ) shift; break ;;
    * ) break ;;
  esac
done

if [ "$LIBRARY_MODE" == "false" ];
then
  setup_addons_tests "$NAME" "$DISTRO" "$PROXY" "$TO_CHANNEL"
  run_smoke_test "$NAME"
  run_core_addons_tests "$NAME"
  DISABLE_COMMUNITY_TESTS="${DISABLE_COMMUNITY_TESTS:-0}"
  if [ "x${DISABLE_COMMUNITY_TESTS}" != "x1" ]; then
    run_community_addons_tests "$NAME"
  fi
  run_gpu_addon_test
  post_addons_tests "$NAME"
fi
