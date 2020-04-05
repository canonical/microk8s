#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling the private registry"

regex_args='([a-zA-Z]+=[a-zA-Z0-9]+(,|))'

read -ra ARGUMENTS <<<"$1"
if [ -z "${ARGUMENTS[@]}" ]; then
  echo "The registry will be created with the default size of 20Gi."
  echo "You can use the \"size\" argument while enabling the registry, eg microk8s.enable registry:size=30Gi"
  declare -A map
  map[\$DISKSIZE]="20Gi"
  "$SNAP/microk8s-enable.wrapper" storage
  echo "Applying registry manifest"
  use_manifest registry apply "$(declare -p map)"
  echo "The registry is enabled"
elif [[ ${ARGUMENTS[@]} =~ $regex_args ]]; then
	IFS=',' read -ra args <<< ${ARGUMENTS[@]}
  REGEX_DISK_SIZE='(^[2-9][0-9]{1,}|^[1-9][0-9]{2,})(Gi$)'
	for arg in "${args[@]}"; do
		read -r key value <<<$(echo $arg | gawk -F "=" '{print $1 ,$2}')
    if [ "$key" != "size" ]; then
      echo "WARNING: The only authorized argument is \"size\", eg  microk8s.enable registry:size=30Gi"
      echo "WARNING: The \"size\" value should match the regex: ([a-zA-Z]+=[a-zA-Z0-9]+(,|))"
      echo "WARNING: Ignoring the key: $key and value $value"
    elif [ "$key" = "size"  ] && [[ ! $value =~ $REGEX_DISK_SIZE ]]; then
      echo "The size of the registry should be higher or equal to 20Gi and match the regex: (^[2-9][0-9]{1,}|^[1-9][0-9]{2,})(Gi$)"
		elif [ "$key" = "size" ] && [[ $value =~ $REGEX_DISK_SIZE ]]; then
      "$SNAP/microk8s-enable.wrapper" storage
      echo "Applying registry manifest"
      declare -A map
      map[\$DISKSIZE]=$value
      use_manifest registry apply "$(declare -p map)"
      echo "The registry is enabled"
      echo "The size of the persistent volume is $value"          
    fi
  done
else
  echo "The only authorized argument is \"size\" and it work as follow: microk8s.enable registry:size=30Gi"
  echo "The arguments should match the following regex ([a-zA-Z]+=[a-zA-Z0-9]+(,|))"
  exit 1
fi
