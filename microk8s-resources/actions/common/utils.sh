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

addon_name() {
    # Extracts the addon from the argument.
    # addons can have arguments in the form of <addon-name>:<arg1>=<value1>;<arg2>=<value2>
    # Example: enable linkerd:proxy-auto-inject=on;other-args=xyz
    # Parameter:
    #   $1 the full addon command
    # Returns:
    #   <addon-name>

    local IFS=':'
    read -ra ADD_ON <<< "$1"
    echo "${ADD_ON[0]}"
}

addon_arguments() {
    # Extracts the addon arguments.
    # Example: enable linkerd:proxy-auto-inject=on;other-args=xyz
    # Parameter:
    #   $1 the addon arguments in array
    # Returns:
    #   add-on arguments array
    local IFS=':'
    read -ra ADD_ON <<< "$1"
    local IFS=';'
    read -ra ARGUMENTS <<< "${ADD_ON[1]}"
    echo "${ARGUMENTS[@]}"
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
    local IP_ADDR="$($SNAP/sbin/ip -o -4 addr list "$DEFAULT_INTERFACE" | $SNAP/usr/bin/gawk '{print $4}' | $SNAP/usr/bin/cut -d/ -f1)"
    if [[ -z "$IP_ADDR" ]]
    then
        echo "none"
    else
        echo "${IP_ADDR}"
    fi
}

get_ips() {
    local IP_ADDR="$($SNAP/bin/hostname -I)"
    if [[ -z "$IP_ADDR" ]]
    then
        echo "none"
    else
        echo "${IP_ADDR}"
    fi
}


produce_server_cert() {
    # Produce the server certificate adding the IP passed as a parameter
    # Parameters:
    # $1 IP we want in the certificate

    local IP_ADDR="$1"

    cp ${SNAP_DATA}/certs/csr.conf.template ${SNAP_DATA}/certs/csr.conf
    if ! [ "$IP_ADDR" == "127.0.0.1" ] && ! [ "$IP_ADDR" == "none" ]
    then
        local ips='' sep=''
        local -i i=3
        for IP_ADDR in "$@"; do
            ips+="${sep}IP.$((i++)) = ${IP_ADDR}"
            sep='\n'
        done
        "$SNAP/bin/sed" -i "s/#MOREIPS/${ips}/g" ${SNAP_DATA}/certs/csr.conf
    else
        "$SNAP/bin/sed" -i 's/#MOREIPS//g' ${SNAP_DATA}/certs/csr.conf
    fi
    openssl req -new -key ${SNAP_DATA}/certs/server.key -out ${SNAP_DATA}/certs/server.csr -config ${SNAP_DATA}/certs/csr.conf
    openssl x509 -req -in ${SNAP_DATA}/certs/server.csr -CA ${SNAP_DATA}/certs/ca.crt -CAkey ${SNAP_DATA}/certs/ca.key -CAcreateserial -out ${SNAP_DATA}/certs/server.crt -days 100000 -extensions v3_ext -extfile ${SNAP_DATA}/certs/csr.conf
}


get_node() {
    # Returns the node name or no_node_found in case no node is present

    KUBECTL="$SNAP/kubectl --kubeconfig=$SNAP/client.config"

    timeout=60
    start_timer="$(date +%s)"
    node_found="yes"
    while ! ($KUBECTL get no | grep -z " Ready") &> /dev/null
    do
      now="$(date +%s)"
      if ! [ -z $timeout ] && [[ "$now" > "$(($start_timer + $timeout))" ]] ; then
        node_found="no"
        echo "no_node_found"
        break
      fi
      sleep 2
    done

    if [ "${node_found}" == "yes" ]
    then
        node="$($KUBECTL get no | $SNAP/bin/grep ' Ready' | $SNAP/usr/bin/gawk '{print $1}')"
        echo $node
    fi
}


drain_node() {
    # Drain node

    node="$(get_node)"
    KUBECTL="$SNAP/kubectl --kubeconfig=$SNAP/client.config"
    if ! [ "${node}" == "no_node_found" ]
    then
        $KUBECTL drain $node --timeout=120s --grace-period=60 --delete-local-data=true || true
    fi
}


uncordon_node() {
    # Un-drain node

    node="$(get_node)"
    KUBECTL="$SNAP/kubectl --kubeconfig=$SNAP/client.config"
    if ! [ "${node}" == "no_node_found" ]
    then
        $KUBECTL uncordon $node || true
    fi
}
