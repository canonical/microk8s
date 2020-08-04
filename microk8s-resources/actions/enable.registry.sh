#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

hostv6=$(getent ahostsv6 localhost | head -n1 | cut -d' ' -f1)
if [ "$hostv6" = "::1" ]; then
  echo "In-cluster registry does not work with ipv6"
  echo "Remove the mapping from ::1 to localhost in /etc/hosts and try again"
  echo "For more details, see https://github.com/ubuntu/microk8s/issues/196"
  exit 1
fi

echo "Enabling the private registry"

"$SNAP/microk8s-enable.wrapper" storage

echo "Applying registry manifest"
use_manifest registry apply

echo "The registry is enabled"
