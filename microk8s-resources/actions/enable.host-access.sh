#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

DEFAULT_IP_ADRESS="10.0.1.1"
read -ra ARGUMENTS <<<"$1"

read -r key value <<<$(echo "${ARGUMENTS[@]}" | gawk -F "=" '{print $1 ,$2}')
read -ra IP_ADDRESS <<< "$value"

KEY_NAME="ip"
if [ ! -z "$key" ] && [ "$key" != $KEY_NAME ]
then
  echo "You should use the the '$KEY_NAME' as key in the argument passed and not '$key'. Eg. microk8s.enable host-access:$KEY_NAME=$IP_ADDRESS";
  exit
fi

if [ -z "$IP_ADDRESS" ]
then
  IP_ADDRESS="$DEFAULT_IP_ADRESS"
else
  if ! valid_ip "${IP_ADDRESS[*]}";
  then
    echo "Bad IP[${IP_ADDRESS}]. Please provide a valid IP address. Default is $DEFAULT_IP_ADRESS";
    exit
  fi
fi
echo "$IP_ADDRESS" > "${SNAP_DATA}/var/lock/host-access-enabled"
echo "Setting ${IP_ADDRESS} as host-access"

run_with_sudo "$SNAP/sbin/ifconfig" lo:microk8s "$IP_ADDRESS" up

# Make loopback ip permanent
NETFILE=/etc/network/interfaces
if [ ! -f $NETFILE ]
then
  echo "WARNING!! File $NETFILE does not exist. Loopback IP[$IP_ADDRESS] will be not added permanently and configuration will be lost on restart"
else
  # Check if the configuration already exists
  CONFIG="\nauto lo:microk8s\niface lo:microk8s inet static\naddress $IP_ADDRESS\nnetmask 255.0.0.0\n"
  CONFIG_1="auto lo:microk8siface lo:microk8s inet staticaddress ${IP_ADDRESS}netmask 255.0.0.0"
  CONTENT=$(cat $NETFILE | tr -d "\n\r")
  if [[ ! $CONTENT == *"${CONFIG_1}"* ]]; then
    echo -e "$CONFIG" >> $NETFILE
  else
    echo "Loopback IP[$IP_ADDRESS] config already exists"
  fi
fi

echo "Host-access is enabled"


