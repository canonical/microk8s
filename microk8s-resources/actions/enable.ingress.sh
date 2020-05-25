#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

read -ra ARGUMENTS <<<"$1"

read -r key value <<<$(echo "${ARGUMENTS[@]}" | gawk -F "=" '{print $1 ,$2}')
read -ra CERT_SECRET <<< "$value"

KEY_NAME="defaultcert"

if [ ! -z "$key" ] && [ "$key" != $KEY_NAME ]
then
  echo "You should use the the '$KEY_NAME' as key in the argument passed and not '$key'. Eg. microk8s.enable ingress:$KEY_NAME=namespace/secret_name";
  exit
fi

echo "Enabling Ingress"

ARCH=$(arch)
TAG="0.25.1"
EXTRA_ARGS="- --publish-status-address=127.0.0.1"
DEFAULT_CERT="- ' '"

if [ ! -z "$CERT_SECRET" ]
then
  DEFAULT_CERT="- --default-ssl-certificate=${CERT_SECRET}"
  echo "Setting ${CERT_SECRET} as default ingress certificate"
fi

declare -A map
map[\$TAG]="$TAG"
map[\$DEFAULT_CERT]="$DEFAULT_CERT"
map[\$EXTRA_ARGS]="$EXTRA_ARGS"
use_manifest ingress apply "$(declare -p map)"

echo "Ingress is enabled"
