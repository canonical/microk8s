#!/usr/bin/env bash
# Create a secret token to be used by MicroDash UI
set -e

source $SNAP/actions/common/utils.sh
# the base bath '/var/snap/microk8s/current/' could also be retrieved from $SNAP_DATA
CALLBACK_TOKEN_FILE="${SNAP_DATA}/credentials/callback-token.txt"

# If token file already exists and has non zero content, use this, otherwise create a new one.
if [ -f ${CALLBACK_TOKEN_FILE} ] && [ ! -z $(cat $CALLBACK_TOKEN_FILE | sed -r '/^\s*$/d') ]
then
    TOKEN=$(<${CALLBACK_TOKEN_FILE})
else
    # TOKEN=$(cat /dev/urandom | tr -dc 'A-Z0-9' | fold -w 64 | head -n 1)
    TOKEN=$(shuf -zer -n64 {A..Z} {0..9} | sed 's/\x0//g' )
    echo "$TOKEN" > ${CALLBACK_TOKEN_FILE}
fi

# setup the magic ip so pod/container can see host
sudo ifconfig lo:1 10.0.2.2 up

KUBECTL="$SNAP/microk8s-kubectl.wrapper"

CHECK_NAMESPACE=$($KUBECTL get namespaces)
if ! echo $CHECK_NAMESPACE | grep "microdash" >/dev/null
then
    $KUBECTL create namespace microdash
fi

CHECK_SECRET=$($KUBECTL -n microdash get secrets)
if echo $CHECK_SECRET | grep "cb-token" >/dev/null
then
    $KUBECTL delete secret cb-token -n microdash
fi

$KUBECTL create secret generic cb-token --from-literal=token.txt="${TOKEN}" --namespace microdash

use_manifest microdash apply
echo "MicroDash enabled"
