#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling the private registry"

"$SNAP/microk8s-enable.wrapper" storage

read -ra ARGUMENTS <<<"$1"
if [ -z "${ARGUMENTS[@]}" ]; then
  echo "Your pvc will be created with the default value of 20Gi. You can customize it with the following command eg: microk8s.enable registry:30Gi"
  declare -A map
  map[\$DISKSIZE]="20Gi"
  echo "Applying registry manifest"
  use_manifest registry apply "$(declare -p map)"
  echo "The registry is enabled"
else
  disk_size="${ARGUMENTS[@]}"
  REGEX_DISK_SIZE='(^[2-9][0-9]{1,}|^[1-9][0-9]{2,})(Gi$)'
  if [[ $disk_size =~ $REGEX_DISK_SIZE ]]; then
    echo "Applying registry manifest"
    declare -A map
    map[\$DISKSIZE]=$disk_size
    use_manifest registry apply "$(declare -p map)"
    echo "The registry is enabled"
  else
    echo "You input value ($disk_size) is not a valid value"
    echo "The value should be Higher or equal to 20Gi"
    exit 1
  fi
fi
