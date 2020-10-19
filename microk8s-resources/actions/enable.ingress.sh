#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

read -ra ARGUMENTS <<<"$1"

read -r key value <<<$(echo "${ARGUMENTS[@]}" | gawk -F "=" '{print $1 ,$2}')
read -ra CERT_SECRET <<< "$value"

KEY_NAME="default-ssl-certificate"

if [ ! -z "$key" ] && [ "$key" != $KEY_NAME ]
then
  echo "Unknown argument '$key'."
  echo "You can use '$KEY_NAME' to load the default TLS certificate from a secret, eg"
  echo "   microk8s enable ingress:$KEY_NAME=namespace/secret_name"
  exit 1
fi

echo "Enabling Ingress"

ARCH=$(arch)
TAG="0.33.0"
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
