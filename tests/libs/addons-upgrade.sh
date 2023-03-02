#!/usr/bin/env bash

function setup_addons_upgrade_tests() {
  local NAME=$1
  local DISTRO=$2
  local PROXY=$3
  create_machine "$NAME" "$DISTRO" "$PROXY"
}

function run_addons_upgrade_tests() {
  local NAME=$1
  local FROM_CHANNEL=$2
  local TO_CHANNEL=$3
  # use 'script' for required tty: https://github.com/lxc/lxd/issues/1724#issuecomment-194416774
  lxc exec "$NAME" -- script -e -c "UPGRADE_MICROK8S_FROM=${FROM_CHANNEL} UPGRADE_MICROK8S_TO=${TO_CHANNEL} pytest -s /root/tests/test-upgrade.py"
}

function post_addons_upgrade_tests() {
  local NAME=$1
  lxc delete "$NAME" --force
}

TEMP=$(getopt -o "lh" \
              --long lib-mode,help,node-name:,distro:,from-channel:,to-channel:,proxy: \
              -n "$(basename "$0")" -- "$@")

if [ $? != 0 ] ; then echo "Terminating..." >&2 ; exit 1 ; fi

eval set -- "$TEMP"

NAME="${NAME-"machine-$RANDOM"}"
DISTRO="${DISTRO-}"
FROM_CHANNEL="${FROM_CHANNEL-}"
TO_CHANNEL="${TO_CHANNEL-}"
PROXY="${PROXY-}"
LIBRARY_MODE=false

while true; do
  case "$1" in
    -l | --lib-mode ) LIBRARY_MODE=true; shift ;;
    --node-name ) NAME="$2"; shift 2 ;;
    --distro ) DISTRO="$2"; shift 2 ;;
    --from-channel ) FROM_CHANNEL="$2"; shift 2 ;;
    --to-channel ) TO_CHANNEL="$2"; shift 2 ;;
    --proxy ) PROXY="$2"; shift 2 ;;
    -h | --help )
      prog=$(basename -s.wrapper "$0")
      echo "Usage: $prog [options...]"
      echo "     --node-name <name> Name to be used for LXD containers"
      echo "         Can also be set by using NAME environment variable"
      echo "     --distro <distro> Distro image to be used for LXD containers Eg. ubuntu:18.04"
      echo "         Can also be set by using DISTRO environment variable"
      echo "     --from-channel <channel> Channel to upgrade from to the channel under testing Eg. latest/beta"
      echo "         Can also be set by using FROM_CHANNEL environment variable"
      echo "     --to-channel <channel> Channel to be tested Eg. latest/edge"
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
  setup_addons_upgrade_tests "$NAME" "$DISTRO" "$PROXY"
  run_addons_upgrade_tests "$NAME" "$FROM_CHANNEL" "$TO_CHANNEL"
  post_addons_upgrade_tests "$NAME"
fi
