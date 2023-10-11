#!/usr/bin/env bash

set -ex

source tests/libs/utils.sh

function run_spread_tests() {
  local NAME=$1
  local DISTRO=$2
  local PROXY=$3
  local TO_CHANNEL=$4

  create_machine "$NAME" "$DISTRO" "$PROXY"

  if [[ ${TO_CHANNEL} =~ /.*/microk8s.*snap ]]
  then
    lxc file push "${TO_CHANNEL}" "$NAME"/tmp/microk8s_latest_amd64.snap
    for i in {1..5}; do lxc exec "$NAME" -- snap install /tmp/microk8s_latest_amd64.snap --dangerous --classic && break || sleep 5; done
  else
    lxc exec "$NAME" -- snap install microk8s --channel="${TO_CHANNEL}" --classic
  fi

  lxc exec "$NAME" -- /snap/bin/microk8s stop
  lxc exec "$NAME" -- sed -i '/\[plugins."io.containerd.grpc.v1.cri"\]/a \ \ disable_apparmor=true' /var/snap/microk8s/current/args/containerd-template.toml
  lxc exec "$NAME" -- /snap/bin/microk8s start
  lxc exec "$NAME" -- /snap/bin/microk8s status --wait-ready --timeout 300
  sleep 45
  lxc exec "$NAME" -- /snap/bin/microk8s kubectl wait pod --all --for=condition=Ready -A --timeout=300s
  lxc exec "$NAME" -- script -e -c "pytest -s /root/tests/test-simple.py"
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
  run_spread_tests "$NAME" "$DISTRO" "$PROXY" "$TO_CHANNEL"
fi
