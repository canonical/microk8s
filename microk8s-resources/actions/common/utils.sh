#!/usr/bin/env bash

exit_if_no_permissions() {
  # test if we can access the default kubeconfig
  if [ ! -r $SNAP_DATA/credentials/client.config ]; then
    echo "Insufficient permissions to access MicroK8s."
    echo "You can either try again with sudo or add the user $USER to the 'microk8s' group:"
    echo ""
    echo "    sudo usermod -a -G microk8s $USER"
    echo ""
    echo "The new group will be available on the user's next login."
    exit 1
  fi
}

exit_if_stopped() {
  # test if the snap is marked as stopped
  if [ -e ${SNAP_DATA}/var/lock/stopped.lock ]
  then
    echo "microk8s is not running, try microk8s.start"
    exit 1
  fi
}

exit_if_service_not_expected_to_start() {
  # exit if a lock is available for the service
  local service="$1"
  if [ -f ${SNAP_DATA}/var/lock/no-${service} ]
  then
    exit 0
  fi
}

is_service_expected_to_start() {
  # return 1 if service is expected to start
  local service="$1"
  if [ -f ${SNAP_DATA}/var/lock/no-${service} ]
  then
    echo "0"
  else
    echo "1"
  fi
}

set_service_not_expected_to_start() {
  # mark service as not starting
  local service="$1"
  touch ${SNAP_DATA}/var/lock/no-${service}
}

set_service_expected_to_start() {
  # mark service as not starting
  local service="$1"
  rm -rf ${SNAP_DATA}/var/lock/no-${service}
}

remove_vxlan_interfaces() {
  links="$(${SNAP}/sbin/ip link show type vxlan | $SNAP/bin/grep -E 'flannel|cilium_vxlan' | $SNAP/usr/bin/gawk '{print $2}' | $SNAP/usr/bin/tr -d :)"
  for link in "$links"
  do
    if ! [ -z "$link" ] && $SNAP/sbin/ip link show ${link} &> /dev/null
    then
      echo "Deleting old ${link} link"
      sudo $SNAP/sbin/ip link delete ${link}
    fi
  done
}

refresh_opt_in_config() {
    # add or replace an option inside the config file.
    # Create the file if doesn't exist
    local opt="--$1"
    local value="$2"
    local config_file="$SNAP_DATA/args/$3"
    local replace_line="$opt=$value"
    if $(grep -qE "^$opt=" $config_file); then
        sudo "$SNAP/bin/sed" -i "s;^$opt=.*;$replace_line;" $config_file
    else
        sudo "$SNAP/bin/sed" -i "$ a $replace_line" "$config_file"
    fi

    if [ -e "${SNAP_DATA}/credentials/callback-tokens.txt" ]
    then
        tokens=$(sudo "$SNAP/bin/cat" "${SNAP_DATA}/credentials/callback-tokens.txt" | "$SNAP/usr/bin/wc" -l)
        if [[ "$tokens" -ge "0" ]]
        then
            sudo -E "$SNAP/usr/bin/python3" "$SNAP/scripts/cluster/distributed_op.py" update_argument "$3" "$opt" "$value"
        fi
    fi
}


nodes_addon() {
    # Enable or disable a, addon across all nodes
    # state should be either 'enable' or 'disable'
    local addon="$1"
    local state="$2"

    if [ -e "${SNAP_DATA}/credentials/callback-tokens.txt" ]
    then
        tokens=$(sudo "$SNAP/bin/cat" "${SNAP_DATA}/credentials/callback-tokens.txt" | "$SNAP/usr/bin/wc" -l)
        if [[ "$tokens" -ge "0" ]]
        then
            sudo -E "$SNAP/usr/bin/python3" "$SNAP/scripts/cluster/distributed_op.py" set_addon "$addon" "$state"
        fi
    fi
}


skip_opt_in_config() {
    # remove an option inside the config file.
    # argument $1 is the option to be removed
    # argument $2 is the configuration file under $SNAP_DATA/args
    local opt="--$1"
    local config_file="$SNAP_DATA/args/$2"
    sudo "${SNAP}/bin/sed" -i '/'"$opt"'/d' "${config_file}"

    if [ -e "${SNAP_DATA}/credentials/callback-tokens.txt" ]
    then
        tokens=$(sudo "$SNAP/bin/cat" "${SNAP_DATA}/credentials/callback-tokens.txt" | "$SNAP/usr/bin/wc" -l)
        if [[ "$tokens" -ge "0" ]]
        then
            sudo -E "$SNAP/usr/bin/python3" "$SNAP/scripts/cluster/distributed_op.py" remove_argument "$2" "$opt"
        fi
    fi
}


restart_service() {
    # restart a systemd service
    # argument $1 is the service name
    sudo systemctl restart "snap.microk8s.daemon-$1.service"

    if [ -e "${SNAP_DATA}/credentials/callback-tokens.txt" ]
    then
        tokens=$(sudo "$SNAP/bin/cat" "${SNAP_DATA}/credentials/callback-tokens.txt" | "$SNAP/usr/bin/wc" -l)
        if [[ "$tokens" -ge "0" ]]
        then
            sudo -E "$SNAP/usr/bin/python3" "$SNAP/scripts/cluster/distributed_op.py" restart "$1"
        fi
    fi
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

wait_for_service_shutdown() {
    # Wait for a service to stop
    # Return  fail if the service did not stop in 30 seconds

    local namespace="$1"
    local labels="$2"
    local shutdown_timeout=30
    local start_timer="$(date +%s)"
    KUBECTL="$SNAP/kubectl --kubeconfig=$SNAP/client.config"

    while ($KUBECTL get po -n "$namespace" -l "$labels" | grep -z " Terminating") &> /dev/null
    do
      now="$(date +%s)"
      if [[ "$now" > "$(($start_timer + $shutdown_timeout))" ]] ; then
        echo "fail"
        break
      fi
      sleep 5
    done
}

get_default_ip() {
    # Get the IP of the default interface
    local DEFAULT_INTERFACE="$($SNAP/bin/netstat -rn | $SNAP/bin/grep '^0.0.0.0' | $SNAP/usr/bin/gawk '{print $NF}' | head -1)"
    local IP_ADDR="$($SNAP/sbin/ip -o -4 addr list "$DEFAULT_INTERFACE" | $SNAP/usr/bin/gawk '{print $4}' | $SNAP/usr/bin/cut -d/ -f1 | head -1)"
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

gen_server_cert() (
    openssl req -new -key ${SNAP_DATA}/certs/server.key -out ${SNAP_DATA}/certs/server.csr -config ${SNAP_DATA}/certs/csr.conf
    openssl x509 -req -in ${SNAP_DATA}/certs/server.csr -CA ${SNAP_DATA}/certs/ca.crt -CAkey ${SNAP_DATA}/certs/ca.key -CAcreateserial -out ${SNAP_DATA}/certs/server.crt -days 100000 -extensions v3_ext -extfile ${SNAP_DATA}/certs/csr.conf
)

gen_proxy_client_cert() (
    openssl req -new -key ${SNAP_DATA}/certs/front-proxy-client.key -out ${SNAP_DATA}/certs/front-proxy-client.csr -config ${SNAP_DATA}/certs/csr.conf -subj "/CN=front-proxy-client"
    openssl x509 -req -in ${SNAP_DATA}/certs/front-proxy-client.csr -CA ${SNAP_DATA}/certs/ca.crt -CAkey ${SNAP_DATA}/certs/ca.key -CAcreateserial -out ${SNAP_DATA}/certs/front-proxy-client.crt -days 100000 -extensions v3_ext -extfile ${SNAP_DATA}/certs/csr.conf
)

produce_certs() {
    # Generate RSA keys if not yet
    for key in serviceaccount.key ca.key server.key front-proxy-client.key; do
        if ! [ -f ${SNAP_DATA}/certs/$key ]; then
            openssl genrsa -out ${SNAP_DATA}/certs/$key 2048
        fi
    done

    # Generate root CA
    if ! [ -f ${SNAP_DATA}/certs/ca.crt ]; then
        openssl req -x509 -new -nodes -key ${SNAP_DATA}/certs/ca.key -subj "/CN=10.152.183.1" -days 10000 -out ${SNAP_DATA}/certs/ca.crt
    fi

    # Produce certificates based on the rendered csr.conf.rendered.
    # The file csr.conf.rendered is compared with csr.conf to determine if a regeneration of the certs must be done.
    #
    # Returns 
    #  0 if no change
    #  1 otherwise. 

    render_csr_conf
    if ! [ -f "${SNAP_DATA}/certs/csr.conf" ]; then
        echo "changeme" >  "${SNAP_DATA}/certs/csr.conf" 
    fi

    local force
    if ! "${SNAP}/usr/bin/cmp" -s "${SNAP_DATA}/certs/csr.conf.rendered" "${SNAP_DATA}/certs/csr.conf"; then
        force=true
        cp ${SNAP_DATA}/certs/csr.conf.rendered ${SNAP_DATA}/certs/csr.conf
    else
        force=false
    fi

    if $force; then
        gen_server_cert
        gen_proxy_client_cert
        echo "1"
    elif [ ! -f "${SNAP_DATA}/certs/front-proxy-client.crt" ]; then
        gen_proxy_client_cert
        echo "1"
    else
        echo "0"
    fi
}

render_csr_conf() {
    # Render csr.conf.template to csr.conf.rendered

    local IP_ADDRESSES="$(get_ips)"

    cp ${SNAP_DATA}/certs/csr.conf.template ${SNAP_DATA}/certs/csr.conf.rendered
    if ! [ "$IP_ADDRESSES" == "127.0.0.1" ] && ! [ "$IP_ADDRESSES" == "none" ]
    then
        local ips='' sep=''
        local -i i=3
        for IP_ADDR in $(echo "$IP_ADDRESSES"); do
            ips+="${sep}IP.$((i++)) = ${IP_ADDR}"
            sep='\n'
        done
        "$SNAP/bin/sed" -i "s/#MOREIPS/${ips}/g" ${SNAP_DATA}/certs/csr.conf.rendered
    else
        "$SNAP/bin/sed" -i 's/#MOREIPS//g' ${SNAP_DATA}/certs/csr.conf.rendered
    fi
}

get_node() {
    # Returns the node name or no_node_found in case no node is present

    KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

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
    KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
    if ! [ "${node}" == "no_node_found" ]
    then
        $KUBECTL drain $node --timeout=120s --grace-period=60 --delete-local-data=true || true
    fi
}


uncordon_node() {
    # Un-drain node

    node="$(get_node)"
    KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"
    if ! [ "${node}" == "no_node_found" ]
    then
        $KUBECTL uncordon $node || true
    fi
}
