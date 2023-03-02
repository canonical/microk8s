#!/usr/bin/env bash

function run_clustering_tests() {
  # Test clustering. This test will create lxc containers or multipass VMs
  # therefore we do not need to run it inside a VM/container
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
}

TEMP=$(getopt -o "lh" \
              --long help,lib-mode,channel:,backend:,lxd-profile: \
              -n "$(basename "$0")" -- "$@")

if [ $? != 0 ] ; then echo "Terminating..." >&2 ; exit 1 ; fi

eval set -- "$TEMP"

BACKEND="${BACKEND-"lxc"}"
CHANNEL_TO_TEST="${CHANNEL_TO_TEST-}"
LXC_PROFILE="${LXC_PROFILE-}"
LIBRARY_MODE=false

while true; do
  case "$1" in
    -l | --lib-mode ) LIBRARY_MODE=true; shift ;;
    --backend ) BACKEND="$2"; shift 2 ;;
    --lxd-profile ) LXC_PROFILE="$2"; shift 2 ;;
    --channel ) CHANNEL_TO_TEST="$2"; shift 2 ;;
    -h | --help )
      prog=$(basename -s.wrapper "$0")
      echo "Usage: $prog [options...]"
      echo "     --backend <backend> Backend to be used for clustering tests Eg. lxc"
      echo "         Can also be set by using BACKEND environment variable"
      echo "     --lxd-profile <path> Profile to be used for lxc backend Eg. tests/lxc/microk8s.profile"
      echo "         Can also be set by using LXC_PROFILE environment variable"
      echo "     --channel <channel> Channel to be tested Eg. latest/edge"
      echo "         Can also be set by using CHANNEL_TO_TEST environment variable"
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
  run_clustering_tests
fi
