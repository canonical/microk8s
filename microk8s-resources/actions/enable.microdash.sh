#!/usr/bin/env bash
# Create a secret token and credentials for basic auth to be used by MicroDash UI
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

# Install host-access addon so pod/container can see host (magic-ip)
"$SNAP/microk8s-enable.wrapper" host-access

if [ -f "${SNAP_DATA}/var/lock/host-access-enabled" ]
then
  HOST_ACCESS_IP=$(<"${SNAP_DATA}/var/lock/host-access-enabled")
else
  echo "Host-access could not be enabled. Cannot continue.."
  exit
fi

# try to parse the username:password from arguments, otherwise use defaults: microadmin/Qwerty
MICRODASH_USER="microadmin"
MICRODASH_PASS=$(openssl passwd -apr1 Qwerty)

read -ra ARGUMENTS <<<"$1"
read -r user pass <<<$(echo "${ARGUMENTS[@]}" | gawk -F "=" '{print $1 ,$2}')

if [ ! -z "$user" ] && [ ! -z "$pass" ]
then
  read -ra MICRODASH_USER <<< "$user"
  read -ra MICRODASH_PASS <<< $(openssl passwd -apr1 $pass)
fi

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

$KUBECTL create secret generic cb-token --from-literal=token.txt="${TOKEN}" --from-literal=host_access_ip="${HOST_ACCESS_IP}" --from-literal=microdash_user="${MICRODASH_USER}" --from-literal=microdash_pass="${MICRODASH_PASS}" --namespace microdash

use_manifest microdash apply
echo "MicroDash enabled"