#!/usr/bin/env bash

exit_if_no_permissions() {
  # test if we can access the default kubeconfig
  if [ ! -r $SNAP_DATA/credentials/client.config ]; then
    echo "Insufficient permissions to access MicroK8s." >&2
    echo "You can either try again with sudo or add the user $USER to the 'microk8s' group:" >&2
    echo "" >&2
    echo "    sudo usermod -a -G microk8s $USER" >&2
    echo "    sudo chown -f -R $USER ~/.kube" >&2
    echo "" >&2
    echo "After this, reload the user groups either via a reboot or by running 'newgrp microk8s'." >&2
    exit 1
  fi
}

exit_if_stopped() {
  # test if the snap is marked as stopped
  if [ -e ${SNAP_DATA}/var/lock/stopped.lock ]
  then
    echo "microk8s is not running, try microk8s start" >&2
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
  run_with_sudo touch ${SNAP_DATA}/var/lock/no-${service}
}

set_service_expected_to_start() {
  # mark service as not starting
  local service="$1"
  rm -rf ${SNAP_DATA}/var/lock/no-${service}
}

remove_vxlan_interfaces() {
  links="$(${SNAP}/sbin/ip link show type vxlan | $SNAP/bin/grep -E 'flannel|cilium_vxlan' | $SNAP/usr/bin/gawk '{print $2}' | $SNAP/usr/bin/tr -d :)"
  for link in $links
  do
    if ! [ -z "$link" ] && $SNAP/sbin/ip link show ${link} &> /dev/null
    then
      echo "Deleting old ${link} link" >&2
      run_with_sudo $SNAP/sbin/ip link delete ${link}
    fi
  done
}

run_with_sudo() {
  # As we call the sudo binary of the host we have to make sure we do not change the LD_LIBRARY_PATH used
  if [ -n "${LD_LIBRARY_PATH-}" ]
  then
    GLOBAL_LD_LIBRARY_PATH="$LD_LIBRARY_PATH"
    local LD_LIBRARY_PATH=""
    if [ "$1" == "preserve_env" ]
    then
      shift
      sudo -E LD_LIBRARY_PATH="$GLOBAL_LD_LIBRARY_PATH" "$@"
    else
      sudo LD_LIBRARY_PATH="$GLOBAL_LD_LIBRARY_PATH" "$@"
    fi
  else
    if [ "$1" == "preserve_env" ]
    then
      shift
      sudo -E "$@"
    else
      sudo "$@"
    fi
  fi
}

get_opt_in_config() {
    # return the value of an option in a configuration file or ""
    local opt="$1"
    local config_file="$SNAP_DATA/args/$2"
    val=""
    if $(grep -qE "^$opt=" $config_file); then
      val="$(grep -E "^$opt" "$config_file" | cut -d'=' -f2)"
    elif $(grep -qE "^$opt " $config_file); then
      val="$(grep -E "^$opt" "$config_file" | cut -d' ' -f2)"
    fi
    echo "$val"
}

refresh_opt_in_local_config() {
    # add or replace an option inside the local config file.
    # Create the file if doesn't exist
    local opt="--$1"
    local value="$2"
    local config_file="$SNAP_DATA/args/$3"
    local replace_line="$opt=$value"
    if $(grep -qE "^$opt=" $config_file); then
        run_with_sudo "$SNAP/bin/sed" -i "s;^$opt=.*;$replace_line;" $config_file
    else
        run_with_sudo "$SNAP/bin/sed" -i "$ a $replace_line" "$config_file"
    fi
}

refresh_opt_in_config() {
    # add or replace an option inside the config file and propagate change.
    # Create the file if doesn't exist
    refresh_opt_in_local_config "$1" "$2" "$3"

    local opt="--$1"
    local value="$2"
    local config_file="$SNAP_DATA/args/$3"
    local replace_line="$opt=$value"

    if [ -e "${SNAP_DATA}/var/lock/ha-cluster" ]
    then
        run_with_sudo preserve_env "$SNAP/usr/bin/python3" "$SNAP/scripts/cluster/distributed_op.py" update_argument "$3" "$opt" "$value"
    fi

    if [ -e "${SNAP_DATA}/credentials/callback-tokens.txt" ]
    then
        tokens=$(run_with_sudo "$SNAP/bin/cat" "${SNAP_DATA}/credentials/callback-tokens.txt" | "$SNAP/usr/bin/wc" -l)
        if [[ "$tokens" -ge "0" ]]
        then
            run_with_sudo preserve_env "$SNAP/usr/bin/python3" "$SNAP/scripts/cluster/distributed_op.py" update_argument "$3" "$opt" "$value"
        fi
    fi
}


nodes_addon() {
    # Enable or disable a, addon across all nodes
    # state should be either 'enable' or 'disable'
    local addon="$1"
    local state="$2"

    if [ -e "${SNAP_DATA}/var/lock/ha-cluster" ]
    then
        run_with_sudo preserve_env "$SNAP/usr/bin/python3" "$SNAP/scripts/cluster/distributed_op.py" set_addon "$addon" "$state"
    fi

    if [ -e "${SNAP_DATA}/credentials/callback-tokens.txt" ]
    then
        tokens=$(run_with_sudo "$SNAP/bin/cat" "${SNAP_DATA}/credentials/callback-tokens.txt" | "$SNAP/usr/bin/wc" -l)
        if [[ "$tokens" -ge "0" ]]
        then
            run_with_sudo preserve_env "$SNAP/usr/bin/python3" "$SNAP/scripts/cluster/distributed_op.py" set_addon "$addon" "$state"
        fi
    fi
}


skip_opt_in_config() {
    # remove an option inside the config file.
    # argument $1 is the option to be removed
    # argument $2 is the configuration file under $SNAP_DATA/args
    local opt="--$1"
    local config_file="$SNAP_DATA/args/$2"
    run_with_sudo "${SNAP}/bin/sed" -i '/'"$opt"'/d' "${config_file}"

    if [ -e "${SNAP_DATA}/var/lock/ha-cluster" ]
    then
        run_with_sudo preserve_env "$SNAP/usr/bin/python3" "$SNAP/scripts/cluster/distributed_op.py" remove_argument "$2" "$opt"
    fi

    if [ -e "${SNAP_DATA}/credentials/callback-tokens.txt" ]
    then
        tokens=$(run_with_sudo "$SNAP/bin/cat" "${SNAP_DATA}/credentials/callback-tokens.txt" | "$SNAP/usr/bin/wc" -l)
        if [[ "$tokens" -ge "0" ]]
        then
            run_with_sudo preserve_env "$SNAP/usr/bin/python3" "$SNAP/scripts/cluster/distributed_op.py" remove_argument "$2" "$opt"
        fi
    fi
}


restart_service() {
    # restart a systemd service
    # argument $1 is the service name

    if [ "$1" == "apiserver" ] || [ "$1" == "proxy" ] || [ "$1" == "kubelet" ] || [ "$1" == "scheduler" ] || [ "$1" == "controller-manager" ]
    then
      if [ -e "${SNAP_DATA}/var/lock/lite.lock" ]
      then
        run_with_sudo preserve_env snapctl restart "microk8s.daemon-kubelite"
      else
        run_with_sudo preserve_env snapctl restart "microk8s.daemon-$1"
      fi
    else
      run_with_sudo preserve_env snapctl restart "microk8s.daemon-$1"
    fi

    if [ -e "${SNAP_DATA}/var/lock/ha-cluster" ]
    then
        run_with_sudo preserve_env "$SNAP/usr/bin/python3" "$SNAP/scripts/cluster/distributed_op.py" restart "$1"
    fi

    if [ -e "${SNAP_DATA}/credentials/callback-tokens.txt" ]
    then
        tokens=$(run_with_sudo "$SNAP/bin/cat" "${SNAP_DATA}/credentials/callback-tokens.txt" | "$SNAP/usr/bin/wc" -l)
        if [[ "$tokens" -ge "0" ]]
        then
            run_with_sudo preserve_env "$SNAP/usr/bin/python3" "$SNAP/scripts/cluster/distributed_op.py" restart "$1"
        fi
    fi
}


arch() {
    echo $SNAP_ARCH
}


snapshotter() {
  # Determine the underlying filesystem that containerd will be running on
  FSTYPE=$(stat -f -c %T "${SNAP_COMMON}")
  # ZFS is supported through the native snapshotter
  if [ "$FSTYPE" = "zfs" ]; then
    echo "native"
  else
    echo "overlayfs"
  fi
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
    if [ "$1" == "apiserver" ] || [ "$1" == "proxy" ] || [ "$1" == "kubelet" ] || [ "$1" == "scheduler" ] || [ "$1" == "controller-manager" ]
    then
      if [ -e "${SNAP_DATA}/var/lock/lite.lock" ]
      then
        service_name="kubelite"
      fi
    fi

    local TRY_ATTEMPT=0
    while ! (run_with_sudo preserve_env snapctl services ${SNAP_NAME}.daemon-${service_name} | grep active) &&
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
    local CNI_INTERFACE="vxlan.calico"
    if [[ -z "$IP_ADDR" ]]
    then
        echo "none"
    else
        if $SNAP/sbin/ifconfig "$CNI_INTERFACE" &> /dev/null
        then
          CNI_IP="$($SNAP/sbin/ip -o -4 addr list "$CNI_INTERFACE" | $SNAP/usr/bin/gawk '{print $4}' | $SNAP/usr/bin/cut -d/ -f1 | head -1)"
          local ips="";
          for ip in $IP_ADDR
          do
            [ "$ip" != "$CNI_IP" ] && ips+="${ips:+ }$ip";
          done
          IP_ADDR="$ips"
        fi
        echo "${IP_ADDR}"
    fi
}

gen_server_cert() (
    export OPENSSL_CONF="/snap/microk8s/current/etc/ssl/openssl.cnf"
    ${SNAP}/usr/bin/openssl req -new -sha256 -key ${SNAP_DATA}/certs/server.key -out ${SNAP_DATA}/certs/server.csr -config ${SNAP_DATA}/certs/csr.conf
    ${SNAP}/usr/bin/openssl x509 -req -sha256 -in ${SNAP_DATA}/certs/server.csr -CA ${SNAP_DATA}/certs/ca.crt -CAkey ${SNAP_DATA}/certs/ca.key -CAcreateserial -out ${SNAP_DATA}/certs/server.crt -days 365 -extensions v3_ext -extfile ${SNAP_DATA}/certs/csr.conf
)

gen_proxy_client_cert() (
    export OPENSSL_CONF="/snap/microk8s/current/etc/ssl/openssl.cnf"
    ${SNAP}/usr/bin/openssl req -new -sha256 -key ${SNAP_DATA}/certs/front-proxy-client.key -out ${SNAP_DATA}/certs/front-proxy-client.csr -config <(sed '/^prompt = no/d' ${SNAP_DATA}/certs/csr.conf) -subj "/CN=front-proxy-client"
    ${SNAP}/usr/bin/openssl x509 -req -sha256 -in ${SNAP_DATA}/certs/front-proxy-client.csr -CA ${SNAP_DATA}/certs/front-proxy-ca.crt -CAkey ${SNAP_DATA}/certs/front-proxy-ca.key -CAcreateserial -out ${SNAP_DATA}/certs/front-proxy-client.crt -days 365 -extensions v3_ext -extfile ${SNAP_DATA}/certs/csr.conf
)

produce_certs() {
    export OPENSSL_CONF="/snap/microk8s/current/etc/ssl/openssl.cnf"
    # Generate RSA keys if not yet
    for key in serviceaccount.key ca.key server.key front-proxy-ca.key front-proxy-client.key; do
        if ! [ -f ${SNAP_DATA}/certs/$key ]; then
            ${SNAP}/usr/bin/openssl genrsa -out ${SNAP_DATA}/certs/$key 2048
        fi
    done

    # Generate apiserver CA
    if ! [ -f ${SNAP_DATA}/certs/ca.crt ]; then
        ${SNAP}/usr/bin/openssl req -x509 -new -sha256 -nodes -days 3650 -key ${SNAP_DATA}/certs/ca.key -subj "/CN=10.152.183.1" -out ${SNAP_DATA}/certs/ca.crt
    fi

    # Generate front proxy CA
    if ! [ -f ${SNAP_DATA}/certs/front-proxy-ca.crt ]; then
        ${SNAP}/usr/bin/openssl req -x509 -new -sha256 -nodes -days 3650 -key ${SNAP_DATA}/certs/front-proxy-ca.key -subj "/CN=front-proxy-ca" -out ${SNAP_DATA}/certs/front-proxy-ca.crt
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
    elif [ ! -f "${SNAP_DATA}/certs/front-proxy-client.crt" ] ||
         [ "$(${SNAP}/usr/bin/openssl < ${SNAP_DATA}/certs/front-proxy-client.crt x509 -noout -issuer)" == "issuer=CN = 127.0.0.1" ]; then
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

wait_for_node() {
  get_node &> /dev/null
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

get_all_addons() {
    actions="$(find "$SNAP/actions" -maxdepth 1 ! -name 'coredns.yaml' -name '*.yaml' -or -name 'enable.*.sh')"
    actions="$(echo "$actions" | sed -e 's/.*[/.]\([^.]*\)\..*/\1/' | sort | uniq)"
    echo $actions
}


function valid_ip() {
# Test an IP address for validity:
# Usage:
#      valid_ip IP_ADDRESS
#      if [[ $? -eq 0 ]]; then echo good; else echo bad; fi
#   OR
#      if valid_ip IP_ADDRESS; then echo good; else echo bad; fi
#
    local  ip=$1
    local  stat=1

    if [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        OIFS=$IFS
        IFS='.'
        ip=($ip)
        IFS=$OIFS
        [[ ${ip[0]} -le 255 && ${ip[1]} -le 255 \
            && ${ip[2]} -le 255 && ${ip[3]} -le 255 ]]
        stat=$?
    fi
    return $stat
}


init_cluster() {
  mkdir -p ${SNAP_DATA}/var/kubernetes/backend
  IP="127.0.0.1"
  # To configure dqlite do:
  # echo "Address: 1.2.3.4:6364" > $STORAGE_DIR/update.yaml
  # after the initialisation but before connecting other nodes
  echo "Address: $IP:19001" > ${SNAP_DATA}/var/kubernetes/backend/init.yaml
  DNS=$($SNAP/bin/hostname)
  mkdir -p $SNAP_DATA/var/tmp/
  cp $SNAP/microk8s-resources/certs/csr-dqlite.conf.template $SNAP_DATA/var/tmp/csr-dqlite.conf
  $SNAP/bin/sed -i 's/HOSTNAME/'"${DNS}"'/g' $SNAP_DATA/var/tmp/csr-dqlite.conf
  $SNAP/bin/sed -i 's/HOSTIP/'"${IP}"'/g' $SNAP_DATA/var/tmp/csr-dqlite.conf
  ${SNAP}/usr/bin/openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes -keyout ${SNAP_DATA}/var/kubernetes/backend/cluster.key -out ${SNAP_DATA}/var/kubernetes/backend/cluster.crt -subj "/CN=k8s" -config $SNAP_DATA/var/tmp/csr-dqlite.conf -extensions v3_ext
  chmod -R o-rwX ${SNAP_DATA}/var/kubernetes/backend/
  if getent group microk8s >/dev/null 2>&1
  then
    chgrp microk8s -R ${SNAP_DATA}/var/kubernetes/backend/ || true
  fi
}


function update_configs {
  # Create the basic tokens
  ca_data=$(cat ${SNAP_DATA}/certs/ca.crt | ${SNAP}/usr/bin/base64 -w 0)
  # Create the client kubeconfig
  run_with_sudo cp ${SNAP}/client.config.template ${SNAP_DATA}/credentials/client.config
  $SNAP/bin/sed -i 's/CADATA/'"${ca_data}"'/g' ${SNAP_DATA}/credentials/client.config
  $SNAP/bin/sed -i 's/NAME/admin/g' ${SNAP_DATA}/credentials/client.config
  if grep admin ${SNAP_DATA}/credentials/known_tokens.csv 2>&1 > /dev/null
  then
    admin_token=`grep admin ${SNAP_DATA}/credentials/known_tokens.csv | cut -d, -f1`
    $SNAP/bin/sed -i 's/AUTHTYPE/token/g' ${SNAP_DATA}/credentials/client.config
    $SNAP/bin/sed -i '/username/d' ${SNAP_DATA}/credentials/client.config
  else
    admin_token=`grep admin ${SNAP_DATA}/credentials/basic_auth.csv | cut -d, -f1`
    $SNAP/bin/sed -i 's/AUTHTYPE/password/g' ${SNAP_DATA}/credentials/client.config
  fi
  $SNAP/bin/sed -i 's/PASSWORD/'"${admin_token}"'/g' ${SNAP_DATA}/credentials/client.config
  # Create the known tokens
  proxy_token=`grep kube-proxy ${SNAP_DATA}/credentials/known_tokens.csv | cut -d, -f1`
  hostname=$(hostname)
  kubelet_token=`grep kubelet-0 ${SNAP_DATA}/credentials/known_tokens.csv | cut -d, -f1`
  controller_token=`grep kube-controller-manager ${SNAP_DATA}/credentials/known_tokens.csv | cut -d, -f1`
  scheduler_token=`grep kube-scheduler ${SNAP_DATA}/credentials/known_tokens.csv | cut -d, -f1`
  # Create the client kubeconfig for the controller
  run_with_sudo cp ${SNAP}/client.config.template ${SNAP_DATA}/credentials/controller.config
  $SNAP/bin/sed -i 's/CADATA/'"${ca_data}"'/g' ${SNAP_DATA}/credentials/controller.config
  $SNAP/bin/sed -i 's/NAME/controller/g' ${SNAP_DATA}/credentials/controller.config
  $SNAP/bin/sed -i '/username/d' ${SNAP_DATA}/credentials/controller.config
  $SNAP/bin/sed -i 's/AUTHTYPE/token/g' ${SNAP_DATA}/credentials/controller.config
  $SNAP/bin/sed -i 's/PASSWORD/'"${controller_token}"'/g' ${SNAP_DATA}/credentials/controller.config
  # Create the client kubeconfig for the scheduler
  run_with_sudo cp ${SNAP}/client.config.template ${SNAP_DATA}/credentials/scheduler.config
  $SNAP/bin/sed -i 's/CADATA/'"${ca_data}"'/g' ${SNAP_DATA}/credentials/scheduler.config
  $SNAP/bin/sed -i 's/NAME/scheduler/g' ${SNAP_DATA}/credentials/scheduler.config
  $SNAP/bin/sed -i '/username/d' ${SNAP_DATA}/credentials/scheduler.config
  $SNAP/bin/sed -i 's/AUTHTYPE/token/g' ${SNAP_DATA}/credentials/scheduler.config
  $SNAP/bin/sed -i 's/PASSWORD/'"${scheduler_token}"'/g' ${SNAP_DATA}/credentials/scheduler.config
  # Create the proxy and kubelet kubeconfig
  run_with_sudo cp ${SNAP}/client.config.template ${SNAP_DATA}/credentials/kubelet.config
  $SNAP/bin/sed -i 's/NAME/kubelet/g' ${SNAP_DATA}/credentials/kubelet.config
  $SNAP/bin/sed -i 's/CADATA/'"${ca_data}"'/g' ${SNAP_DATA}/credentials/kubelet.config
  $SNAP/bin/sed -i '/username/d' ${SNAP_DATA}/credentials/kubelet.config
  $SNAP/bin/sed -i 's/AUTHTYPE/token/g' ${SNAP_DATA}/credentials/kubelet.config
  $SNAP/bin/sed -i 's/PASSWORD/'"${kubelet_token}"'/g' ${SNAP_DATA}/credentials/kubelet.config
  run_with_sudo cp ${SNAP}/client.config.template ${SNAP_DATA}/credentials/proxy.config
  $SNAP/bin/sed -i 's/NAME/kubeproxy/g' ${SNAP_DATA}/credentials/proxy.config
  $SNAP/bin/sed -i 's/CADATA/'"${ca_data}"'/g' ${SNAP_DATA}/credentials/proxy.config
  $SNAP/bin/sed -i '/username/d' ${SNAP_DATA}/credentials/proxy.config
  $SNAP/bin/sed -i 's/AUTHTYPE/token/g' ${SNAP_DATA}/credentials/proxy.config
  $SNAP/bin/sed -i 's/PASSWORD/'"${proxy_token}"'/g' ${SNAP_DATA}/credentials/proxy.config
  $SNAP/microk8s-stop.wrapper || true
  $SNAP/microk8s-start.wrapper
}

is_apiserver_ready() {
  if (${SNAP}/usr/bin/curl -L --cert ${SNAP_DATA}/certs/server.crt --key ${SNAP_DATA}/certs/server.key --cacert ${SNAP_DATA}/certs/ca.crt https://127.0.0.1:16443/readyz | grep -z "ok") &> /dev/null
  then
    return 0
  else
    return 1
  fi
}

start_all_containers() {
    for task in $("${SNAP}/microk8s-ctr.wrapper" task ls | sed -n '1!p' | awk '{print $1}')
    do
        "${SNAP}/microk8s-ctr.wrapper" task resume $task &>/dev/null || true
    done
}

stop_all_containers() {
    for task in $("${SNAP}/microk8s-ctr.wrapper" task ls | sed -n '1!p' | awk '{print $1}')
    do
        "${SNAP}/microk8s-ctr.wrapper" task pause $task &>/dev/null || true
        "${SNAP}/microk8s-ctr.wrapper" task kill -s SIGKILL $task &>/dev/null || true
    done
}

remove_all_containers() {
    stop_all_containers
    for task in $("${SNAP}/microk8s-ctr.wrapper" task ls | sed -n '1!p' | awk '{print $1}')
    do
        "${SNAP}/microk8s-ctr.wrapper" task delete --force $task &>/dev/null || true
    done

    for container in $("${SNAP}/microk8s-ctr.wrapper" containers ls | sed -n '1!p' | awk '{print $1}')
    do
        "${SNAP}/microk8s-ctr.wrapper" container delete --force $container &>/dev/null || true
    done
}

get_container_shim_pids() {
    ps -e -o pid= -o args= | grep -v 'grep' | sed -e 's/^ *//; s/\s\s*/\t/;' | grep -w '/snap/microk8s/.*/bin/containerd-shim' | cut -f1
}

kill_all_container_shims() {
    run_with_sudo systemctl kill snap.microk8s.daemon-kubelite.service --signal=SIGKILL &>/dev/null || true
    run_with_sudo systemctl kill snap.microk8s.daemon-kubelet.service --signal=SIGKILL &>/dev/null || true
    run_with_sudo systemctl kill snap.microk8s.daemon-containerd.service --signal=SIGKILL &>/dev/null || true
}

is_first_boot() {
  # Return 0 if this is the first start after the host booted.
  # The argument $1 is a directory that may contain a last-start-date file
  # The last-start-date file contains a date in seconds
  # if that date is prior to the creation date of /proc/1 we assume this is the first
  # time after the host booted
  if ! [ -e "$1/last-start-date" ] ||
     ! [ -e /proc/1 ]
  then
    return 1
  else
    last_start=$("$SNAP/bin/cat" "$1/last-start-date")
    if [ -e /proc/stat ] &&
       grep btime /proc/stat
    then
      boot_time=$(grep btime /proc/stat | cut -d' ' -f2)
    else
      boot_time=$(date -r  /proc/1 +%s)
    fi
    echo "Last time service started was $last_start and the host booted at $boot_time"
    if [ "$last_start" -le "$boot_time" ]
    then
      return 0
    else
      return 1
    fi
  fi
}

mark_boot_time() {
  # place the current time in the "$1"/last-start-date file
  now=$(date +%s)
  echo "$now" > "$1"/last-start-date
}
