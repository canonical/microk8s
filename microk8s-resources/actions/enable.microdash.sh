#!/usr/bin/env bash
# Create a secret token and credentials for basic auth to be used by MicroDash UI
set -e

source $SNAP/actions/common/utils.sh
# the base bath '/var/snap/microk8s/current/' could also be retrieved from $SNAP_DATA
CALLBACK_TOKEN_FILE="${SNAP_DATA}/credentials/callback-token.txt"
MICRODASH_BASIC_AUTH_FILE="${SNAP_DATA}/credentials/.microdash_basic_auth"

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

# try to parse the username:password from arguments, otherwise use defaults: microadmin/MicroK8s
MICRODASH_USER="microadmin"
MICRODASH_PASS=$(openssl passwd -apr1 MicroK8s)

read -ra ARGUMENTS <<<"$1"
read -r user pass <<<$(echo "${ARGUMENTS[@]}" | gawk -F "=" '{print $1 ,$2}')

if [ ! -z "$user" ] && [ ! -z "$pass" ]
then
  read -ra MICRODASH_USER <<< "$user"
  read -ra MICRODASH_PASS <<< $(openssl passwd -apr1 $pass)
fi

# check if nginx basic auth file exists and use that to extract credentials
# sample:
#   user1:$apr1$/woC1jnP$KAh0SsVn5qeSMjTtn0E9Q0
# Hashed password can be created with this command:
#   openssl passwd -apr1 your_password
if [ -f ${MICRODASH_BASIC_AUTH_FILE} ] && [ ! -z $(cat $MICRODASH_BASIC_AUTH_FILE | sed -r '/^\s*$/d') ]
then
    CONTENT=$(<${MICRODASH_BASIC_AUTH_FILE})
    read -r user pass <<<$(echo "${CONTENT[@]}" | gawk -F ":" '{print $1 ,$2}')
    if [ ! -z "$user" ] && [ ! -z "$pass" ]
    then
      read -ra MICRODASH_USER <<< "$user"
      read -ra MICRODASH_PASS <<< "$pass"
    else
      echo -e "\nERROR:\nThe file $MICRODASH_BASIC_AUTH_FILE does not include proper data. File content:\n\n $CONTENT\n"
      echo -e "The username-password pair should be created in NGINX basic auth format using tools like openssl, apache2-utils or httpd-tools."
      echo -e "For example, you can create a password using the command: \n\n openssl passwd -apr1 your_password \n"
      echo -e "and then use it along with a desired username by editing the file and creating content like:\n"
      DUMMY_PASS=$(openssl passwd -apr1 your_password)
      echo -e "user1:$DUMMY_PASS \n"
      exit
    fi
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
BROWSER_IP=$($KUBECTL get services -n microdash | grep microdash-service | awk '{print $3}')
echo "Point your browser at http://$BROWSER_IP and when prompted enter user '$MICRODASH_USER' and the selected password. If nothing selected, default is MicroK8s"