#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

read -ra ARGUMENTS <<< $(addon_arguments "$1")

CERTIFICATE_KEY_NAME="default-ssl-certificate"
BACKEND_KEY_NAME="default-backend-service"

for ARG in "${ARGUMENTS[@]}"
do
  read -r key value <<<$(echo "$ARG" | gawk -F "=" '{print $1 ,$2}')

  if [ ! -z "$key" ]
  then
    if [ "$key" != $CERTIFICATE_KEY_NAME ] && [ "$key" != $BACKEND_KEY_NAME ]
    then
      echo "Unknown argument '$key'."
      echo "You can use '$CERTIFICATE_KEY_NAME' to load the default TLS certificate from a secret, eg"
      echo "You can use '$BACKEND_KEY_NAME' to change the default backend service"
      echo "microk8s enable ingress:$CERTIFICATE_KEY_NAME=namespace/secret_name;$BACKEND_KEY_NAME=namespace/service_name"
      exit 1
    elif [ "$key" == $CERTIFICATE_KEY_NAME ]
    then
      read -ra CERT_SECRET <<< "$value"
    elif [ "$key" == $BACKEND_KEY_NAME ]
    then
      read -ra BACKEND_SERVICE <<< "$value"
    fi
  fi
done

echo "Enabling Ingress"

ARCH=$(arch)
TAG="v0.35.0"
EXTRA_ARGS="- --publish-status-address=127.0.0.1"
DEFAULT_CERT="- ' '"
DEFAULT_BACKEND_SERVICE="- ' '"

if [ ! -z "$CERT_SECRET" ]
then
  DEFAULT_CERT="- --default-ssl-certificate=${CERT_SECRET}"
  echo "Setting ${CERT_SECRET} as default ingress certificate"
fi

if [ ! -z "$BACKEND_SERVICE" ]
then
  DEFAULT_BACKEND_SERVICE="- --default-backend-service=${BACKEND_SERVICE}"
  echo "Setting ${BACKEND_SERVICE} as default ingress service"
fi

declare -A map
map[\$TAG]="$TAG"
map[\$DEFAULT_CERT]="$DEFAULT_CERT"
map[\$DEFAULT_BACKEND_SERVICE]="$BACKEND_SERVICE"
map[\$EXTRA_ARGS]="$EXTRA_ARGS"
use_manifest ingress apply "$(declare -p map)"

echo "Ingress is enabled"
