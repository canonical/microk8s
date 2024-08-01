#!/usr/bin/env bash

source tests/libs/utils.sh

TEMP=$(getopt -o "h" \
              --long help,distro:,from-channel:,to-channel:,proxy: \
              -n "$(basename "$0")" -- "$@")

if [ $? != 0 ] ; then echo "Terminating..." >&2 ; exit 1 ; fi

eval set -- "$TEMP"

DISTRO="${DISTRO-}"
FROM_CHANNEL="${FROM_CHANNEL-}"
TO_CHANNEL="${TO_CHANNEL-}"
PROXY="${PROXY-}"

while true; do
  case "$1" in
    --distro ) DISTRO="$2"; shift 2 ;;
    --from-channel ) FROM_CHANNEL="$2"; shift 2 ;;
    --to-channel ) TO_CHANNEL="$2"; shift 2 ;;
    --proxy ) PROXY="$2"; shift 2 ;;
    -h | --help ) 
      prog=$(basename -s.wrapper "$0")
      echo "Usage: $prog [options...] <distro> <from-channel> <to-channel> <proxy>"
      echo "     --distro <distro> Distro image to be used for LXD containers Eg. ubuntu:18.04"
      echo "         Can also be set by using DISTRO environment variable"
      echo "     --from-channel <channel> Channel to upgrade from to the channel under testing Eg. latest/beta"
      echo "         Can also be set by using FROM_CHANNEL environment variable"
      echo "     --to-channel <channel> Channel to be tested Eg. latest/edge"
      echo "         Can also be set by using TO_CHANNEL environment variable"
      echo "     --proxy <url> Proxy url to be used by the nodes"
      echo "         Can also be set by using PROXY environment variable"
      echo
      exit ;;
    -- ) shift; break ;;
    * ) break ;;
  esac
done

set -uex

setup_tests "$@"

DISABLE_AIRGAP_TESTS="${DISABLE_AIRGAP_TESTS:-0}"
if [ "x${DISABLE_AIRGAP_TESTS}" != "x1" ]; then
  . tests/libs/airgap.sh
fi

. tests/libs/clustering.sh

. tests/libs/addons-upgrade.sh

. tests/libs/upgrade-path.sh

. tests/libs/addons.sh
