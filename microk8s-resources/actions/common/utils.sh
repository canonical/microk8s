#!/usr/bin/env bash

exit_if_stopped() {
  # test if the snap is marked as stopped
  if [ -e ${SNAP_DATA}/var/lock/stopped.lock ]
  then
    echo "microk8s is not running, try microk8s.start"
    exit 1
  fi
}


refresh_opt_in_config() {
    # add or replace an option inside the config file.
    # Create the file if doesn't exist
    local opt="--$1"
    local value="$2"
    local config_file="$SNAP_DATA/args/$3"
    local replace_line="$opt=$value"
    if $(grep -qE "^$opt=" $config_file); then
        sudo "$SNAP/bin/sed" -i "s/^$opt=.*/$replace_line/" $config_file
    else
        sudo "$SNAP/bin/sed" -i "$ a $replace_line" "$config_file"
    fi
}


skip_opt_in_config() {
    # remove an option inside the config file.
    # argument $1 is the option to be removed
    # argument $2 is the configuration file under $SNAP_DATA/args
    local opt="--$1"
    local config_file="$SNAP_DATA/args/$2"
    sudo "${SNAP}/bin/sed" -i '/'"$opt"'/d' "${config_file}"
}


arch() {
    echo $SNAP_ARCH
}


use_manifest() {
    # Perform an action (apply or delete) on a manifest.
    # Optionally replace strings in the manifest
    #
    # Parameters:
    # $1 the name of the manifest. Should be ${SNAP}/actions/ and should not
    #    include the trailing .yaml eg ingress, dns
    # $2 the action to be performed on the manifest, eg apply, delete
    # $3 (optional) an associative array with keys the string to be replaced and value what to
    #    replace with. The string $ARCH is always injected to this array.
    #
    local manifest="$1.yaml"; shift
    local action="$1"; shift
    if ! [ "$#" = "0" ]
    then
        eval "declare -A items="${1#*=}
    else
        declare -A items
    fi
    local tmp_manifest="${SNAP_USER_DATA}/tmp/temp.${manifest}"
    items[\$ARCH]=$(arch)

    mkdir -p ${SNAP_USER_DATA}/tmp
    cp "${SNAP}/actions/${manifest}" "${tmp_manifest}"
    for i in "${!items[@]}"
    do
        "$SNAP/bin/sed" -i 's@'$i'@'"${items[$i]}"'@g' "${tmp_manifest}"
    done
    "$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" "$action" -f "${tmp_manifest}"
    use_manifest_result="$?"
    rm "${tmp_manifest}"
}


wait_for_service() {
    # Wait for a service to start
    # Return fail if the service did not start in 30 seconds
    local service_name="$1"
    local TRY_ATTEMPT=0
    while ! (sudo systemctl is-active --quiet snap.${SNAP_NAME}.daemon-${service_name}) &&
          ! [ ${TRY_ATTEMPT} -eq 30 ]
    do
        TRY_ATTEMPT=$((TRY_ATTEMPT+1))
        sleep 1
    done
    if [ ${TRY_ATTEMPT} -eq 30 ]
    then
        echo "fail"
    fi
}


get_default_ip() {
    # Get the IP of the default interface
    local DEFAULT_INTERFACE="$($SNAP/bin/netstat -rn | $SNAP/bin/grep '^0.0.0.0' | $SNAP/usr/bin/gawk '{print $NF}' | head -1)"
    local IP_ADDR="$($SNAP/sbin/ifconfig "$DEFAULT_INTERFACE" | $SNAP/bin/grep 'inet ' | $SNAP/usr/bin/gawk '{print $2}' | $SNAP/bin/sed -e 's/addr://')"
    echo ${IP_ADDR}
}


produce_server_cert() {
    # Produce the server certificate adding the IP passed as a parameter
    # Parameters:
    # $1 IP we want in the certificate

    local IP_ADDR="$1"

    cp ${SNAP}/certs/csr.conf.template ${SNAP_DATA}/certs/csr.conf
    if ! [ "$IP_ADDR" == "127.0.0.1" ] && ! [ "$IP_ADDR" == "" ]
    then
        "$SNAP/bin/sed" -i 's/#MOREIPS/IP.3 = '"${IP_ADDR}"'/g' ${SNAP_DATA}/certs/csr.conf
    else
        "$SNAP/bin/sed" -i 's/#MOREIPS//g' ${SNAP_DATA}/certs/csr.conf
    fi
    openssl req -new -key ${SNAP_DATA}/certs/server.key -out ${SNAP_DATA}/certs/server.csr -config ${SNAP_DATA}/certs/csr.conf
    openssl x509 -req -in ${SNAP_DATA}/certs/server.csr -CA ${SNAP_DATA}/certs/ca.crt -CAkey ${SNAP_DATA}/certs/ca.key -CAcreateserial -out ${SNAP_DATA}/certs/server.crt -days 100000 -extensions v3_ext -extfile ${SNAP_DATA}/certs/csr.conf
}

maybe_cache_juju_operator_images() {
    if [ ! -f /snap/bin/juju.cache-images ]; then
        echo "No supported version of Juju installed."
        exit 0
    fi
    /snap/bin/juju.cache-images
}
