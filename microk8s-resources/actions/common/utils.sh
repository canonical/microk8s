#!/usr/bin/env bash

get_microk8s_group() {
  if is_strict
  then
    echo "snap_microk8s"
  else
    echo "microk8s"
  fi
}

get_microk8s_or_cis_group() {
  if [ -e $SNAP_DATA/var/lock/cis-hardening ]
  then
    echo "root"
  else
    get_microk8s_group
  fi
}


exit_if_no_permissions() {
  # test if we can access the default kubeconfig
  if [ ! -r $SNAP_DATA/credentials/client.config ]; then
    local group=$(get_microk8s_group)

    echo "Insufficient permissions to access MicroK8s." >&2
    echo "You can either try again with sudo or add the user $USER to the '${group}' group:" >&2
    echo "" >&2
    echo "    sudo usermod -a -G ${group} $USER" >&2
    echo "    sudo chown -R $USER ~/.kube" >&2
    echo "" >&2
    echo "After this, reload the user groups either via a reboot or by running 'newgrp ${group}'." >&2
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
  run_with_sudo $SNAP/bin/touch ${SNAP_DATA}/var/lock/no-${service}
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
  if [ "$1" == "preserve_env" ]; then
    shift
  fi
  if (is_strict); then
    "$@"
  else
    local SAVE_LD_LIBRARY_PATH="${LD_LIBRARY_PATH}"
    LD_LIBRARY_PATH="" sudo -E PATH="${PATH}" LD_LIBRARY_PATH="${SAVE_LD_LIBRARY_PATH}" PYTHONPATH="${PYTHONPATH:-}" "$@"
  fi
}

get_opt_in_config() {
    # return the value of an option in a configuration file or ""
    local opt="$1"
    local config_file="$SNAP_DATA/args/$2"
    val=""
    if $($SNAP/bin/grep -qE "^$opt=" $config_file); then
      val="$($SNAP/bin/grep -E "^$opt" "$config_file" | $SNAP/usr/bin/cut -d'=' -f2)"
    elif $($SNAP/bin/grep -qE "^$opt " $config_file); then
      val="$($SNAP/bin/grep -E "^$opt" "$config_file" | $SNAP/usr/bin/cut -d' ' -f2)"
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
    if $($SNAP/bin/grep -qE "^$opt=" $config_file); then
        run_with_sudo "$SNAP/bin/sed" -i "s@^$opt=.*@$replace_line@" $config_file
    else
        run_with_sudo "$SNAP/bin/sed" -i "1i$replace_line" "$config_file"
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
        run_with_sudo preserve_env "$SNAP/usr/bin/python3" "$SNAP/scripts/wrappers/distributed_op.py" update_argument "$3" "$opt" "$value"
    fi

    if [ -e "${SNAP_DATA}/credentials/callback-tokens.txt" ]
    then
        tokens=$(run_with_sudo "$SNAP/bin/cat" "${SNAP_DATA}/credentials/callback-tokens.txt" | "$SNAP/usr/bin/wc" -l)
        if [[ "$tokens" -ge "0" ]]
        then
            run_with_sudo preserve_env "$SNAP/usr/bin/python3" "$SNAP/scripts/wrappers/distributed_op.py" update_argument "$3" "$opt" "$value"
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
        run_with_sudo preserve_env "$SNAP/usr/bin/python3" "$SNAP/scripts/wrappers/distributed_op.py" set_addon "$addon" "$state"
    fi

    if [ -e "${SNAP_DATA}/credentials/callback-tokens.txt" ]
    then
        tokens=$(run_with_sudo "$SNAP/bin/cat" "${SNAP_DATA}/credentials/callback-tokens.txt" | "$SNAP/usr/bin/wc" -l)
        if [[ "$tokens" -ge "0" ]]
        then
            run_with_sudo preserve_env "$SNAP/usr/bin/python3" "$SNAP/scripts/wrappers/distributed_op.py" set_addon "$addon" "$state"
        fi
    fi
}


skip_opt_in_local_config() {
    # remove an option inside the config file.
    # argument $1 is the option to be removed
    # argument $2 is the configuration file under $SNAP_DATA/args
    local opt="--$1"
    local config_file="$SNAP_DATA/args/$2"

    # regex is "$opt[= ]", otherwise we remove all arguments with the same prefix
    run_with_sudo "${SNAP}/bin/sed" -i '/'"$opt[= ]"'/d' "${config_file}"
}


skip_opt_in_config() {
    # remove an option inside the config file.
    # argument $1 is the option to be removed
    # argument $2 is the configuration file under $SNAP_DATA/args
    skip_opt_in_local_config "$1" "$2"

    local opt="--$1"

    if [ -e "${SNAP_DATA}/var/lock/ha-cluster" ]
    then
        run_with_sudo preserve_env "$SNAP/usr/bin/python3" "$SNAP/scripts/wrappers/distributed_op.py" remove_argument "$2" "$opt"
    fi

    if [ -e "${SNAP_DATA}/credentials/callback-tokens.txt" ]
    then
        tokens=$(run_with_sudo "$SNAP/bin/cat" "${SNAP_DATA}/credentials/callback-tokens.txt" | "$SNAP/usr/bin/wc" -l)
        if [[ "$tokens" -ge "0" ]]
        then
            run_with_sudo preserve_env "$SNAP/usr/bin/python3" "$SNAP/scripts/wrappers/distributed_op.py" remove_argument "$2" "$opt"
        fi
    fi
}


remove_args() {
  # Removes arguments from respective service
  # argument $1: the service
  # rest of arguments: the arguments to be removed
  local service_name="$1"
  shift
  local args=("$@")
  for arg in "${args[@]}"; do
    if $SNAP/bin/grep -q "$arg" "$SNAP_DATA/args/$service_name"; then
      echo "Removing argument: $arg from $service_name"
      skip_opt_in_local_config "$arg" "$service_name"
    fi
  done
}


sanitise_args_kubeapi_server() {
  # Function to sanitise arguments for API server
  local args=(
    # Removed klog flags from 1.26+
    # https://github.com/kubernetes/enhancements/blob/master/keps/sig-instrumentation/2845-deprecate-klog-specific-flags-in-k8s-components/README.md
    "log-dir"
    "log-file"
    "log-flush-frequency"
    "logtostderr"
    "alsologtostderr"
    "one-output"
    "stderrthreshold"
    "log-file-max-size"
    "skip-log-headers"
    "add-dir-header"
    "skip-headers"
    "log-backtrace-at"
    # Remove insecure-port from 1.24+
    "insecure-port"
    "insecure-bind-address"
    "port"
    "address"
    # Remove service-account-api-audiences from 1.25+
    # https://github.com/kubernetes/kubernetes/commit/92707cafbb67a5664324eb891ef70ab3d1dd4a97
    "service-account-api-audiences"
    # extra
    "feature-gates=RemoveSelfLink"
    "experimental-encryption-provider-config"
    "target-ram-mb"
  )

  remove_args "kube-apiserver" "${args[@]}"
}


sanitise_args_kubelet() {
  # Function to sanitise arguments for kubelet
  local args=(
    # Removed klog flags from 1.26+
    # https://github.com/kubernetes/enhancements/blob/master/keps/sig-instrumentation/2845-deprecate-klog-specific-flags-in-k8s-components/README.md
    "log-dir"
    "log-file"
    "log-flush-frequency"
    "logtostderr"
    "alsologtostderr"
    "one-output"
    "stderrthreshold"
    "log-file-max-size"
    "skip-log-headers"
    "add-dir-header"
    "skip-headers"
    "log-backtrace-at"
    # Removed dockershim flags from 1.24+
    # https://github.com/kubernetes/enhancements/issues/2221
    "docker-endpoint"
    "image-pull-progress-deadline"
    "network-plugin"
    "cni-conf-dir"
    "cni-bin-dir"
    "cni-cache-dir"
    "network-plugin-mtu"
    # extra
    "experimental-kernel-memcg-notification"
    "pod-infra-container-image"
    "experimental-dockershim-root-directory"
    "non-masquerade-cidr"
    # Remove container-runtime flag from 1.27+
    "container-runtime"
  )

  remove_args "kubelet" "${args[@]}"

  # Remove 'DevicePlugins=true' from feature-gates from 1.28+
  $SNAP/bin/sed -i 's,DevicePlugins=true,,' "$SNAP_DATA/args/kubelet"
}


sanitise_args_kube_proxy() {
  # Function to sanitise arguments for kube-proxy

  # userspace proxy-mode is not allowed on the 1.26+ k8s
  # https://kubernetes.io/blog/2022/11/18/upcoming-changes-in-kubernetes-1-26/#removal-of-kube-proxy-userspace-modes
  if $SNAP/bin/grep -- "--proxy-mode=userspace" $SNAP_DATA/args/kube-proxy
  then
    echo "Removing --proxy-mode=userspace flag from kube-proxy, since it breaks Calico."
    skip_opt_in_local_config "proxy-mode" "kube-proxy"
  fi

  local args=(
    # Removed klog flags from 1.26+
    # https://github.com/kubernetes/enhancements/blob/master/keps/sig-instrumentation/2845-deprecate-klog-specific-flags-in-k8s-components/README.md
    "log-dir"
    "log-file"
    "log-flush-frequency"
    "logtostderr"
    "alsologtostderr"
    "one-output"
    "stderrthreshold"
    "log-file-max-size"
    "skip-log-headers"
    "add-dir-header"
    "skip-headers"
    "log-backtrace-at"
  )

  remove_args "kube-proxy" "${args[@]}"
}


sanitise_args_kube_controller_manager() {
  # Function to sanitise arguments for kube-controller-manager
  local args=(
    # Removed klog flags from 1.26+
    # https://github.com/kubernetes/enhancements/blob/master/keps/sig-instrumentation/2845-deprecate-klog-specific-flags-in-k8s-components/README.md
    "log-dir"
    "log-file"
    "log-flush-frequency"
    "logtostderr"
    "alsologtostderr"
    "one-output"
    "stderrthreshold"
    "log-file-max-size"
    "skip-log-headers"
    "add-dir-header"
    "skip-headers"
    "log-backtrace-at"
    # Remove insecure ports from 1.24+
    # https://github.com/kubernetes/kubernetes/pull/96216/files
    "address"
    "port"
    # extra
    "experimental-cluster-signing-duration"
  )

  remove_args "kube-controller-manager" "${args[@]}"
}


sanitise_args_kube_scheduler() {
  # Function to sanitise arguments for kube-scheduler
  local args=(
    # Removed klog flags from 1.26+
    # https://github.com/kubernetes/enhancements/blob/master/keps/sig-instrumentation/2845-deprecate-klog-specific-flags-in-k8s-components/README.md
    "log-dir"
    "log-file"
    "log-flush-frequency"
    "logtostderr"
    "alsologtostderr"
    "one-output"
    "stderrthreshold"
    "log-file-max-size"
    "skip-log-headers"
    "add-dir-header"
    "skip-headers"
    "log-backtrace-at"
    # Remove insecure ports from 1.24+
    # https://github.com/kubernetes/kubernetes/pull/96345/files
    "address"
    "port"
  )

  remove_args "kube-scheduler" "${args[@]}"
}


restart_service() {
    # restart a systemd service
    # argument $1 is the service name

    if [ "$1" == "apiserver" ] || [ "$1" == "proxy" ] || [ "$1" == "kubelet" ] || [ "$1" == "scheduler" ] || [ "$1" == "controller-manager" ]
    then
      run_with_sudo preserve_env snapctl restart "microk8s.daemon-kubelite"
    else
      run_with_sudo preserve_env snapctl restart "microk8s.daemon-$1"
    fi

    if [ -e "${SNAP_DATA}/var/lock/ha-cluster" ]
    then
        run_with_sudo preserve_env "$SNAP/usr/bin/python3" "$SNAP/scripts/wrappers/distributed_op.py" restart "$1"
    fi

    if [ -e "${SNAP_DATA}/credentials/callback-tokens.txt" ]
    then
        tokens=$(run_with_sudo "$SNAP/bin/cat" "${SNAP_DATA}/credentials/callback-tokens.txt" | "$SNAP/usr/bin/wc" -l)
        if [[ "$tokens" -ge "0" ]]
        then
            run_with_sudo preserve_env "$SNAP/usr/bin/python3" "$SNAP/scripts/wrappers/distributed_op.py" restart "$1"
        fi
    fi
}


arch() {
  case "${SNAP_ARCH}" in
    ppc64el)  echo ppc64le        ;;
    *)        echo "${SNAP_ARCH}" ;;
  esac
}


snapshotter() {
  # Determine the underlying filesystem that containerd will be running on
  FSTYPE=$($SNAP/usr/bin/stat -f -c %T "${SNAP_COMMON}")
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
    local tmp_manifest="${SNAP_USER_DATA}/tmp/temp.yaml"
    items[\$ARCH]=$(arch)

    $SNAP/bin/mkdir -p ${SNAP_USER_DATA}/tmp
    $SNAP/bin/cp "${SNAP}/addons/core/addons/${manifest}" "${tmp_manifest}"
    for i in "${!items[@]}"
    do
        "$SNAP/bin/sed" -i 's@'$i'@'"${items[$i]}"'@g' "${tmp_manifest}"
    done
    "$SNAP/kubectl" "--kubeconfig=$SNAP_DATA/credentials/client.config" "$action" -f "${tmp_manifest}"
    use_manifest_result="$?"
    $SNAP/bin/rm "${tmp_manifest}"
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
    local start_timer="$($SNAP/bin/date +%s)"
    KUBECTL="$SNAP/kubectl --kubeconfig=$SNAP/client.config"

    while ($KUBECTL get po -n "$namespace" -l "$labels" | $SNAP/bin/grep -z " Terminating") &> /dev/null
    do
      now="$($SNAP/bin/date +%s)"
      if [[ "$now" > "$(($start_timer + $shutdown_timeout))" ]] ; then
        echo "fail"
        break
      fi
      sleep 5
    done
}

get_default_ip() {
    # Get the IP of the default interface
    local DEFAULT_INTERFACE="$($SNAP/sbin/ip route show default | $SNAP/usr/bin/gawk '{for(i=1; i<NF; i++) if($i=="dev") print$(i+1)}' | head -1)"
    local IP_ADDR="$($SNAP/sbin/ip -o -4 addr list "$DEFAULT_INTERFACE" | $SNAP/usr/bin/gawk '{print $4}' | $SNAP/usr/bin/cut -d/ -f1 | head -1)"

    if [[ -z "$IP_ADDR" ]]; then
        local IP_ADDR="$($SNAP/sbin/ip route get 255.255.255.255 | $SNAP/usr/bin/gawk '{for(i=1; i<NF; i++) if($i=="src") print$(i+1)}' | head -1)"
    fi

    if [[ -z "$IP_ADDR" ]]
    then
        echo "none"
    else
        echo "${IP_ADDR}"
    fi
}

get_ips() {
    local IP_ADDR="$($SNAP/bin/hostname -I | $SNAP/bin/sed 's/169\.254\.[0-9]\{1,3\}\.[0-9]\{1,3\}//g')"
    # Retrieve all IPs from CNI interfaces. These will need to be ignored.
    CNI_IPS=""
    for CNI_INTERFACE in vxlan.calico flannel.1 cni0 ovn0; do
        CNI_IP="$($SNAP/sbin/ip -o -4 addr list "$CNI_INTERFACE" 2>/dev/null | $SNAP/bin/grep -v 'inet 169.254' | $SNAP/usr/bin/gawk '{print $4}' | $SNAP/usr/bin/cut -d/ -f1 | head -1)"
        CNI_IPS="/$CNI_IP/$CNI_IPS"
    done

    if [[ -z "$IP_ADDR" ]]; then
        echo "none"
    else
        local ips="";
        for ip in $IP_ADDR; do
            # Append IP address only iff not in cni IP addresses
            (echo "$CNI_IPS" | $SNAP/bin/grep -q "/$ip/") || ips+="${ips:+ }$ip";
        done
        echo "$ips"
    fi
}

gen_server_cert() (
    "${SNAP}/openssl.wrapper" req -new -sha256 -key ${SNAP_DATA}/certs/server.key -out ${SNAP_DATA}/certs/server.csr -config ${SNAP_DATA}/certs/csr.conf
    "${SNAP}/openssl.wrapper" x509 -req -sha256 -in ${SNAP_DATA}/certs/server.csr -CA ${SNAP_DATA}/certs/ca.crt -CAkey ${SNAP_DATA}/certs/ca.key -CAcreateserial -out ${SNAP_DATA}/certs/server.crt -days 365 -extensions v3_ext -extfile ${SNAP_DATA}/certs/csr.conf
)

gen_proxy_client_cert() (
    "${SNAP}/openssl.wrapper" req -new -sha256 -key ${SNAP_DATA}/certs/front-proxy-client.key -out ${SNAP_DATA}/certs/front-proxy-client.csr -config <(sed '/^prompt = no/d' ${SNAP_DATA}/certs/csr.conf) -subj "/CN=front-proxy-client"
    "${SNAP}/openssl.wrapper" x509 -req -sha256 -in ${SNAP_DATA}/certs/front-proxy-client.csr -CA ${SNAP_DATA}/certs/front-proxy-ca.crt -CAkey ${SNAP_DATA}/certs/front-proxy-ca.key -CAcreateserial -out ${SNAP_DATA}/certs/front-proxy-client.crt -days 365 -extensions v3_ext -extfile ${SNAP_DATA}/certs/csr.conf
)

create_user_certs_and_configs() {
  create_user_certificates
  create_user_kubeconfigs
}

create_user_certificates() {
  hostname=$($SNAP/bin/hostname | $SNAP/usr/bin/tr '[:upper:]' '[:lower:]')
  generate_csr_with_sans "/CN=system:node:$hostname/O=system:nodes" "${SNAP_DATA}/certs/kubelet.key" | sign_certificate > "${SNAP_DATA}/certs/kubelet.crt"
  generate_csr /CN=admin/O=system:masters "${SNAP_DATA}/certs/client.key" | sign_certificate > "${SNAP_DATA}/certs/client.crt"
  generate_csr /CN=system:kube-proxy "${SNAP_DATA}/certs/proxy.key" | sign_certificate > "${SNAP_DATA}/certs/proxy.crt"
  generate_csr /CN=system:kube-scheduler "${SNAP_DATA}/certs/scheduler.key" | sign_certificate > "${SNAP_DATA}/certs/scheduler.crt"
  generate_csr /CN=system:kube-controller-manager "${SNAP_DATA}/certs/controller.key" | sign_certificate > "${SNAP_DATA}/certs/controller.crt"
  generate_csr /CN=kube-apiserver-kubelet-client/O=system:masters "${SNAP_DATA}/certs/apiserver-kubelet-client.key" | sign_certificate > "${SNAP_DATA}/certs/apiserver-kubelet-client.crt"
}

create_user_kubeconfigs() {
  hostname=$($SNAP/bin/hostname | $SNAP/usr/bin/tr '[:upper:]' '[:lower:]')
  create_kubeconfig_x509 "client.config" "admin" ${SNAP_DATA}/certs/client.crt ${SNAP_DATA}/certs/client.key ${SNAP_DATA}/certs/ca.crt
  create_kubeconfig_x509 "controller.config" "system:kube-controller-manager" ${SNAP_DATA}/certs/controller.crt ${SNAP_DATA}/certs/controller.key ${SNAP_DATA}/certs/ca.crt
  create_kubeconfig_x509 "scheduler.config" "system:kube-scheduler" ${SNAP_DATA}/certs/scheduler.crt ${SNAP_DATA}/certs/scheduler.key ${SNAP_DATA}/certs/ca.crt
  create_kubeconfig_x509 "proxy.config" "system:kube-proxy" ${SNAP_DATA}/certs/proxy.crt ${SNAP_DATA}/certs/proxy.key ${SNAP_DATA}/certs/ca.crt
  create_kubeconfig_x509 "kubelet.config" "system:node:${hostname}" ${SNAP_DATA}/certs/kubelet.crt ${SNAP_DATA}/certs/kubelet.key ${SNAP_DATA}/certs/ca.crt
}

create_worker_kubeconfigs() {
  # $1: (Optional) API server IP, defaults to IP address from traefik-template.yaml (or empty)
  # $2: (Optional) API server port, defaults to port from traefik-template.yaml

  # NOTE(neoaggelos): Examples for how "${var%:*}" and ${var##*:} below behave
  # apiserver_proxy_listen=":16443"       => apiserver_default=""           port_default="16443"
  # apiserver_proxy_listen="1.1.1.1:6443" => apiserver_default="1.1.1.1"    port_default="6443"
  # apiserver_proxy_listen="[::1]:16443"  => apiserver_default="[::1]"      port_default="16443"
  # apiserver_proxy_listen=""             => apiserver_default=""           port_default=""

  local apiserver_proxy_listen="$($SNAP/bin/cat $SNAP_DATA/args/traefik/traefik-template.yaml | $SNAP/bin/grep "address:" | $SNAP/usr/bin/cut -d'"' -f2)"
  local apiserver_default="${apiserver_proxy_listen%:*}"    # drop last ':' and everything after
  local port_default="${apiserver_proxy_listen##*:}"        # drop last ':' and everything before

  local apiserver="${1:-$apiserver_default}"
  local port="${2:-$port_default}"

  hostname=$($SNAP/bin/hostname | $SNAP/usr/bin/tr '[:upper:]' '[:lower:]')
  create_kubeconfig_x509 "proxy.config" "system:kube-proxy" ${SNAP_DATA}/certs/proxy.crt ${SNAP_DATA}/certs/proxy.key ${SNAP_DATA}/certs/ca.remote.crt "${apiserver}" "${port}"
  create_kubeconfig_x509 "kubelet.config" "system:node:${hostname}" ${SNAP_DATA}/certs/kubelet.crt ${SNAP_DATA}/certs/kubelet.key ${SNAP_DATA}/certs/ca.remote.crt "${apiserver}" "${port}"
}

create_kubeconfig_x509() {
  # Create a kubeconfig file with x509 auth
  # $1: the name of the config file
  # $2: the user to use al login
  # $3: path to certificate file
  # $4: path to certificate key file
  # $5: path to ca file
  # $6: (optional) API server IP, optional defaults to 127.0.0.1
  # $7: (optional) API server port, optional defaults to the port of the current node

  kubeconfig=$1
  user=$2
  cert=$3
  key=$4
  ca=$5

  # optional arguments
  apiserver="${6:-"127.0.0.1"}"
  apiserver_port="$($SNAP/bin/cat $SNAP_DATA/args/kube-apiserver | $SNAP/bin/grep -- "--secure-port" | $SNAP/usr/bin/tr "=" " " | $SNAP/usr/bin/gawk '{print $2}')"
  port="${7:-${apiserver_port}}"

  ca_data=$($SNAP/bin/cat ${ca} | ${SNAP}/usr/bin/base64 -w 0)
  cert_data=$($SNAP/bin/cat ${cert} | ${SNAP}/usr/bin/base64 -w 0)
  key_data=$($SNAP/bin/cat ${key} | ${SNAP}/usr/bin/base64 -w 0)
  config_file="${SNAP_DATA}/credentials/${kubeconfig}"

  $SNAP/bin/cp "${SNAP}/client-x509.config.template" "${config_file}"
  $SNAP/bin/sed -i 's/CADATA/'"${ca_data}"'/g' "${config_file}"
  $SNAP/bin/sed -i 's/NAME/'"${user}"'/g' "${config_file}"
  $SNAP/bin/sed -i 's/PATHTOCERT/'"${cert_data}"'/g' "${config_file}"
  $SNAP/bin/sed -i 's/PATHTOKEYCERT/'"${key_data}"'/g' "${config_file}"
  $SNAP/bin/sed -i 's/client-certificate/client-certificate-data/g' "${config_file}"
  $SNAP/bin/sed -i 's/client-key/client-key-data/g' "${config_file}"
  $SNAP/bin/sed -i 's/127.0.0.1/'"${apiserver}"'/g' "${config_file}"
  $SNAP/bin/sed -i 's/16443/'"${port}"'/g' "${config_file}"
}

produce_certs() {
    # Generate RSA keys if not yet
    for key in serviceaccount.key ca.key server.key front-proxy-ca.key front-proxy-client.key; do
        if ! [ -f ${SNAP_DATA}/certs/$key ]; then
            "${SNAP}/openssl.wrapper" genrsa -out ${SNAP_DATA}/certs/$key 2048
        fi
    done

    # Generate apiserver CA
    if ! [ -f ${SNAP_DATA}/certs/ca.crt ]; then
        "${SNAP}/openssl.wrapper" req -x509 -new -sha256 -nodes -days 3650 -key ${SNAP_DATA}/certs/ca.key -subj "/CN=10.152.183.1" -out ${SNAP_DATA}/certs/ca.crt
    fi

    # Generate front proxy CA
    if ! [ -f ${SNAP_DATA}/certs/front-proxy-ca.crt ]; then
        "${SNAP}/openssl.wrapper" req -x509 -new -sha256 -nodes -days 3650 -key ${SNAP_DATA}/certs/front-proxy-ca.key -subj "/CN=front-proxy-ca" -out ${SNAP_DATA}/certs/front-proxy-ca.crt
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
        $SNAP/bin/cp ${SNAP_DATA}/certs/csr.conf.rendered ${SNAP_DATA}/certs/csr.conf
    else
        force=false
    fi

    if $force; then
        gen_server_cert
        gen_proxy_client_cert
        echo "1"
    elif [ ! -f "${SNAP_DATA}/certs/front-proxy-client.crt" ] ||
         [ "$("${SNAP}/openssl.wrapper" < ${SNAP_DATA}/certs/front-proxy-client.crt x509 -noout -issuer)" == "issuer=CN = 127.0.0.1" ]; then
        gen_proxy_client_cert
        echo "1"
    else
        echo "0"
    fi
}

ensure_server_ca() {
    # ensure the server.crt is issued by ca.crt
    # in a ca chain it is only verified that the server.crt is issued by the intermediate ca
    # if current csr.conf is invalid, regenerate front-proxy-client certificates as well

    if ! "${SNAP}/openssl.wrapper" verify -no-CAfile -no-CApath -partial_chain -trusted ${SNAP_DATA}/certs/ca.crt ${SNAP_DATA}/certs/server.crt &>/dev/null
    then
        csr_modified="$(ensure_csr_conf_conservative)"
        gen_server_cert

        if [[ "$csr_modified" -eq  "1" ]]
        then
            gen_proxy_client_cert
        fi

        echo "1"
    else
        echo "0"
    fi
}

check_csr_conf() {
    # if no argument is given, default csr.conf will be checked
    csr_conf="${1:-${SNAP_DATA}/certs/csr.conf}"
    "${SNAP}/openssl.wrapper" req -new -config $csr_conf -noout -nodes -keyout /dev/null &>/dev/null
}

refresh_csr_conf() {
    render_csr_conf
    $SNAP/bin/cp ${SNAP_DATA}/certs/csr.conf.rendered ${SNAP_DATA}/certs/csr.conf
}

ensure_csr_conf_conservative() {
    # ensure csr.conf is a valid csr config file; if not:
    # copy csr.conf.rendered if valid, or render new if not

    if ! check_csr_conf
    then
        if ! check_csr_conf ${SNAP_DATA}/certs/csr.conf.rendered
        then
          render_csr_conf
        fi

        $SNAP/bin/cp ${SNAP_DATA}/certs/csr.conf.rendered ${SNAP_DATA}/certs/csr.conf
        echo "1"
    else
        echo "0"
    fi
}

render_csr_conf() {
    # Render csr.conf.template to csr.conf.rendered

    local IP_ADDRESSES="$(get_ips)"

    $SNAP/bin/cp ${SNAP_DATA}/certs/csr.conf.template ${SNAP_DATA}/certs/csr.conf.rendered
    if ! [ "$IP_ADDRESSES" == "127.0.0.1" ] && ! [ "$IP_ADDRESSES" == "none" ]
    then
        local ips='' sep=''
        local -i i=3
        for IP_ADDR in $(echo "$IP_ADDRESSES"); do
            local ip_id="IP.$((i++))"
	    while $SNAP/bin/grep '^'"${ip_id}" ${SNAP_DATA}/certs/csr.conf.template > /dev/null ; do
              ip_id="IP.$((i++))"
            done
            ips+="${sep}${ip_id} = ${IP_ADDR}"
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
    start_timer="$($SNAP/bin/date +%s)"
    node_found="yes"
    while ! ($KUBECTL get no | $SNAP/bin/grep -z " Ready") &> /dev/null
    do
      now="$($SNAP/bin/date +%s)"
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
  $SNAP/bin/mkdir -p ${SNAP_DATA}/var/kubernetes/backend
  IP="127.0.0.1"
  # To configure dqlite do:
  # echo "Address: 1.2.3.4:6364" > $STORAGE_DIR/update.yaml
  # after the initialisation but before connecting other nodes
  echo "Address: $IP:19001" > ${SNAP_DATA}/var/kubernetes/backend/init.yaml
  DNS=$($SNAP/bin/hostname)
  $SNAP/bin/mkdir -p $SNAP_DATA/var/tmp/
  $SNAP/bin/cp $SNAP/certs/csr-dqlite.conf.template $SNAP_DATA/var/tmp/csr-dqlite.conf
  $SNAP/bin/sed -i 's/HOSTNAME/'"${DNS}"'/g' $SNAP_DATA/var/tmp/csr-dqlite.conf
  $SNAP/bin/sed -i 's/HOSTIP/'"${IP}"'/g' $SNAP_DATA/var/tmp/csr-dqlite.conf
  "${SNAP}/openssl.wrapper" req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes -keyout ${SNAP_DATA}/var/kubernetes/backend/cluster.key -out ${SNAP_DATA}/var/kubernetes/backend/cluster.crt -subj "/CN=k8s" -config $SNAP_DATA/var/tmp/csr-dqlite.conf -extensions v3_ext
  $SNAP/bin/chmod -R o-rwX ${SNAP_DATA}/var/kubernetes/backend/
  local group=$(get_microk8s_group)
  if getent group ${group} >/dev/null 2>&1
  then
    $SNAP/bin/chgrp ${group} -R --preserve=mode ${SNAP_DATA}/var/kubernetes/backend/ || true
  fi
}


function update_configs {
  # Create the basic tokens
  ca_data=$($SNAP/bin/cat ${SNAP_DATA}/certs/ca.crt | ${SNAP}/usr/bin/base64 -w 0)
  # Create the client kubeconfig
  run_with_sudo $SNAP/bin/cp ${SNAP}/client.config.template ${SNAP_DATA}/credentials/client.config
  $SNAP/bin/sed -i 's/CADATA/'"${ca_data}"'/g' ${SNAP_DATA}/credentials/client.config
  $SNAP/bin/sed -i 's/NAME/admin/g' ${SNAP_DATA}/credentials/client.config
  if $SNAP/bin/grep admin ${SNAP_DATA}/credentials/known_tokens.csv 2>&1 > /dev/null
  then
    admin_token=`$SNAP/bin/grep admin ${SNAP_DATA}/credentials/known_tokens.csv | $SNAP/usr/bin/cut -d, -f1`
    $SNAP/bin/sed -i 's/AUTHTYPE/token/g' ${SNAP_DATA}/credentials/client.config
    $SNAP/bin/sed -i '/username/d' ${SNAP_DATA}/credentials/client.config
  else
    admin_token=`$SNAP/bin/grep admin ${SNAP_DATA}/credentials/basic_auth.csv | $SNAP/usr/bin/cut -d, -f1`
    $SNAP/bin/sed -i 's/AUTHTYPE/password/g' ${SNAP_DATA}/credentials/client.config
  fi
  $SNAP/bin/sed -i 's/PASSWORD/'"${admin_token}"'/g' ${SNAP_DATA}/credentials/client.config
  # Create the known tokens
  proxy_token=`$SNAP/bin/grep kube-proxy ${SNAP_DATA}/credentials/known_tokens.csv | $SNAP/usr/bin/cut -d, -f1`
  hostname=$($SNAP/bin/hostname | $SNAP/usr/bin/tr '[:upper:]' '[:lower:]')
  kubelet_token=`$SNAP/bin/grep kubelet-0, ${SNAP_DATA}/credentials/known_tokens.csv | $SNAP/usr/bin/cut -d, -f1`
  controller_token=`$SNAP/bin/grep kube-controller-manager ${SNAP_DATA}/credentials/known_tokens.csv | $SNAP/usr/bin/cut -d, -f1`
  scheduler_token=`$SNAP/bin/grep kube-scheduler ${SNAP_DATA}/credentials/known_tokens.csv | $SNAP/usr/bin/cut -d, -f1`
  # Create the client kubeconfig for the controller
  run_with_sudo $SNAP/bin/cp ${SNAP}/client.config.template ${SNAP_DATA}/credentials/controller.config
  $SNAP/bin/sed -i 's/CADATA/'"${ca_data}"'/g' ${SNAP_DATA}/credentials/controller.config
  $SNAP/bin/sed -i 's/NAME/controller/g' ${SNAP_DATA}/credentials/controller.config
  $SNAP/bin/sed -i '/username/d' ${SNAP_DATA}/credentials/controller.config
  $SNAP/bin/sed -i 's/AUTHTYPE/token/g' ${SNAP_DATA}/credentials/controller.config
  $SNAP/bin/sed -i 's/PASSWORD/'"${controller_token}"'/g' ${SNAP_DATA}/credentials/controller.config
  # Create the client kubeconfig for the scheduler
  run_with_sudo $SNAP/bin/cp ${SNAP}/client.config.template ${SNAP_DATA}/credentials/scheduler.config
  $SNAP/bin/sed -i 's/CADATA/'"${ca_data}"'/g' ${SNAP_DATA}/credentials/scheduler.config
  $SNAP/bin/sed -i 's/NAME/scheduler/g' ${SNAP_DATA}/credentials/scheduler.config
  $SNAP/bin/sed -i '/username/d' ${SNAP_DATA}/credentials/scheduler.config
  $SNAP/bin/sed -i 's/AUTHTYPE/token/g' ${SNAP_DATA}/credentials/scheduler.config
  $SNAP/bin/sed -i 's/PASSWORD/'"${scheduler_token}"'/g' ${SNAP_DATA}/credentials/scheduler.config
  # Create the proxy and kubelet kubeconfig
  run_with_sudo $SNAP/bin/cp ${SNAP}/client.config.template ${SNAP_DATA}/credentials/kubelet.config
  $SNAP/bin/sed -i 's/NAME/kubelet/g' ${SNAP_DATA}/credentials/kubelet.config
  $SNAP/bin/sed -i 's/CADATA/'"${ca_data}"'/g' ${SNAP_DATA}/credentials/kubelet.config
  $SNAP/bin/sed -i '/username/d' ${SNAP_DATA}/credentials/kubelet.config
  $SNAP/bin/sed -i 's/AUTHTYPE/token/g' ${SNAP_DATA}/credentials/kubelet.config
  $SNAP/bin/sed -i 's/PASSWORD/'"${kubelet_token}"'/g' ${SNAP_DATA}/credentials/kubelet.config
  run_with_sudo $SNAP/bin/cp ${SNAP}/client.config.template ${SNAP_DATA}/credentials/proxy.config
  $SNAP/bin/sed -i 's/NAME/kubeproxy/g' ${SNAP_DATA}/credentials/proxy.config
  $SNAP/bin/sed -i 's/CADATA/'"${ca_data}"'/g' ${SNAP_DATA}/credentials/proxy.config
  $SNAP/bin/sed -i '/username/d' ${SNAP_DATA}/credentials/proxy.config
  $SNAP/bin/sed -i 's/AUTHTYPE/token/g' ${SNAP_DATA}/credentials/proxy.config
  $SNAP/bin/sed -i 's/PASSWORD/'"${proxy_token}"'/g' ${SNAP_DATA}/credentials/proxy.config
  $SNAP/microk8s-stop.wrapper || true
  $SNAP/microk8s-start.wrapper
}

is_apiserver_ready() {
  if (${SNAP}/usr/bin/curl -L --cert ${SNAP_DATA}/certs/server.crt --key ${SNAP_DATA}/certs/server.key --cacert ${SNAP_DATA}/certs/ca.crt https://127.0.0.1:16443/readyz | $SNAP/bin/grep -z "ok") &> /dev/null
  then
    return 0
  else
    return 1
  fi
}

start_all_containers() {
    for task in $("${SNAP}/microk8s-ctr.wrapper" task ls | $SNAP/bin/sed -n '1!p' | $SNAP/usr/bin/gawk '{print $1}')
    do
        "${SNAP}/microk8s-ctr.wrapper" task resume $task &>/dev/null || true
    done
}

stop_all_containers() {
    for task in $("${SNAP}/microk8s-ctr.wrapper" task ls | $SNAP/bin/sed -n '1!p' | $SNAP/usr/bin/gawk '{print $1}')
    do
        "${SNAP}/microk8s-ctr.wrapper" task pause $task &>/dev/null || true
        "${SNAP}/microk8s-ctr.wrapper" task kill -s SIGKILL $task &>/dev/null || true
    done
}

remove_all_containers() {
    stop_all_containers
    for task in $("${SNAP}/microk8s-ctr.wrapper" task ls | $SNAP/bin/sed -n '1!p' | $SNAP/usr/bin/gawk '{print $1}')
    do
        "${SNAP}/microk8s-ctr.wrapper" task delete --force $task &>/dev/null || true
    done

    for container in $("${SNAP}/microk8s-ctr.wrapper" containers ls | $SNAP/bin/sed -n '1!p' | $SNAP/usr/bin/gawk '{print $1}')
    do
        "${SNAP}/microk8s-ctr.wrapper" container delete $container &>/dev/null || true
    done
}

get_container_shim_pids() {
    $SNAP/bin/ps -e -o pid= -o args= | $SNAP/bin/grep -v 'grep' | $SNAP/bin/sed -e 's/^ *//; s/\s\s*/\t/;' | $SNAP/bin/grep -w '/snap/microk8s/.*/bin/containerd-shim' | $SNAP/usr/bin/cut -f1
}

kill_all_container_shims() {
  run_with_sudo systemctl kill snap.microk8s.daemon-kubelite.service --signal=SIGKILL &>/dev/null || true
  run_with_sudo systemctl kill snap.microk8s.daemon-containerd.service --signal=SIGKILL &>/dev/null || true
}

is_first_boot() {
  # Return 0 if this is the first start after the host booted.
  # The argument $1 is a directory that may contain a last-start-date file
  # The last-start-date file contains a date in seconds
  # if that date is prior to the creation date of /proc/1 we assume this is the first
  # time after the host booted
  # Note, lxc shares the same /proc/stat as the host
  if ! [ -e "$1/last-start-date" ] ||
     ! [ -e /proc/1 ]
  then
    return 1
  else
    last_start=$("$SNAP/bin/cat" "$1/last-start-date")
    if [ -e /proc/stat ] &&
       $SNAP/bin/grep btime /proc/stat &&
       ! $SNAP/bin/grep lxc /proc/1/environ
    then
      boot_time=$($SNAP/bin/grep btime /proc/stat | $SNAP/usr/bin/cut -d' ' -f2)
    else
      boot_time=$($SNAP/bin/date -r  /proc/1 +%s)
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
  now=$($SNAP/bin/date +%s)
  echo "$now" > "$1"/last-start-date
}

try_copy_users_to_snap_microk8s() {
  # try copy users from microk8s to snap_microk8s group
  if getent group microk8s >/dev/null 2>&1 &&
     getent group snap_microk8s >/dev/null 2>&1
  then
    for m in $($SNAP/usr/bin/members microk8s)
    do
      echo "Processing user $m"
      if ! usermod -a -G snap_microk8s $m
      then
        echo "Failed to migrate user $m to snap_microk8s group"
      fi
    done
  else
    echo "One of the microk8s or snap_microk8s groups is missing"
  fi
}

cluster_agent_port() {
  port="25000"
  if $SNAP/bin/grep -e port "${SNAP_DATA}"/args/cluster-agent &> /dev/null
  then
    port=$($SNAP/bin/cat "${SNAP_DATA}"/args/cluster-agent | "$SNAP"/usr/bin/gawk '{print $2}')
  fi

  echo "$port"
}

server_cert_check() {
  "${SNAP}/openssl.wrapper" x509 -in "$SNAP_DATA"/certs/server.crt -outform der | ${SNAP}/usr/bin/sha256sum | $SNAP/usr/bin/cut -d' ' -f1 | $SNAP/usr/bin/cut -c1-12
}

generate_csr_with_sans() {
  # Description:
  #   Generate CSR for component certificates, including hostname and node IP addresses
  #   as SubjectAlternateNames. The CSR PEM is printed to stdout. Arguments are:
  #   1. The certificate subject, e.g. "/CN=system:node:$hostname/O=system:nodes"
  #   2. The path to write the private key, e.g. "$SNAP_DATA/certs/kubelet.key"
  #
  # Notes:
  #   - Subject is /CN=system:node:$hostname/O=system:nodes
  #   - Node hostname and IP addresses are added as Subject Alternate Names
  #
  # Example usage:
  #   generate_csr_with_sans /CN=system:node:$hostname/O=system:nodes $SNAP_DATA/certs/kubelet.key > $SNAP_DATA/certs/kubelet.csr

  # Add DNS name and IP addresses as subjectAltName
  hostname=$($SNAP/bin/hostname | $SNAP/usr/bin/tr '[:upper:]' '[:lower:]')
  subjectAltName="DNS:$hostname"
  for ip in $(get_ips); do
    subjectAltName="$subjectAltName, IP:$ip"
  done

  # generate key if it does not exist
  if [ ! -f "$2" ]; then
    "${SNAP}/openssl.wrapper" genrsa -out "$2" 2048
    $SNAP/bin/chown 0:0 "$2" || true
    $SNAP/bin/chmod 0600 "$2" || true
  fi

  # generate csr
  "${SNAP}/openssl.wrapper" req -new -sha256 -subj "$1" -key "$2" -addext "subjectAltName = $subjectAltName"
}

generate_csr() {
  # Description:
  #   Generate CSR for component certificates. The CSR PEM is written to stdout. Arguments are:
  #   1. The certificate subject, e.g. "/CN=system:kube-scheduler"
  #   2. The path to write the private key, e.g. "$SNAP_DATA/certs/scheduler.key"
  #
  # Example usage:
  #   generate_csr /CN=system:kube-scheduler $SNAP_DATA/certs/scheduler.key > $SNAP_DATA/certs/scheduler.csr

  # generate key if it does not exist
  if [ ! -f "$2" ]; then
    "${SNAP}/openssl.wrapper" genrsa -out "$2" 2048
    $SNAP/bin/chown 0:0 "$2" || true
    $SNAP/bin/chmod 0600 "$2" || true
  fi

  # generate csr
  "${SNAP}/openssl.wrapper" req -new -sha256 -subj "$1" -key "$2"
}

sign_certificate() {
  # Description:
  #   Sign a certificate signing request (CSR) using the MicroK8s cluster CA.
  #   The CSR is read through stdin, and the signed certificate is printed to stdout.
  #
  # Notes:
  #   - Read from stdin and write to stdout, so no temporary files are required.
  #   - Any SubjectAlternateNames that are included in the CSR are added to the certificate.
  #
  # Example usage:
  #   cat component.csr | sign_certificate > component.crt

  # We need to use the request more than once, use this trick to grab stdin and save it in '$csr'
  csr="$($SNAP/bin/cat)"

  # Parse SANs from the CSR and add them to the certificate extensions (if any)
  extensions=""
  alt_names="$(echo "$csr" | "${SNAP}/openssl.wrapper" req -text | $SNAP/bin/grep "X509v3 Subject Alternative Name:" -A1 | $SNAP/usr/bin/tail -n 1 | $SNAP/bin/sed 's,IP Address:,IP:,g')"
  if test "x$alt_names" != "x"; then
    extensions="subjectAltName = $alt_names"
  fi

  # Sign certificate and print to stdout
  echo "$csr" | "${SNAP}/openssl.wrapper" x509 -req -sha256 -CA "${SNAP_DATA}/certs/ca.crt" -CAkey "${SNAP_DATA}/certs/ca.key" -CAcreateserial -days 3650 -extfile <(echo "${extensions}")
}


exit_if_low_memory_guard() {
  if [ -e ${SNAP_DATA}/var/lock/low-memory-guard.lock ]
  then
    echo ''
    echo 'This node does not have enough RAM to host the Kubernetes control plane services'
    echo 'and join the database quorum. You may consider joining this node as a worker'
    echo 'node to a cluster.'
    echo ''
    echo 'If you would still like to start the control plane services, start MicroK8s with:'
    echo ''
    echo '    microk8s start --disable-low-memory-guard'
    echo ''
    exit 1
  fi
}

refresh_calico_if_needed() {
    # Call the python script that does the calico update if needed
    "$SNAP/usr/bin/python3" "$SNAP/scripts/calico/upgrade.py"
}

remove_docker_specific_args() {
  # Remove docker specific arguments and return 0 if kubelet needs to be restarted
  if $SNAP/bin/grep -e "\-\-network-plugin" ${SNAP_DATA}/args/kubelet ||
    $SNAP/bin/grep -e "\-\-cni-conf-dir" ${SNAP_DATA}/args/kubelet ||
    $SNAP/bin/grep -e "\-\-cni-bin-dir" ${SNAP_DATA}/args/kubelet
  then
    skip_opt_in_local_config network-plugin kubelet
    skip_opt_in_local_config cni-conf-dir kubelet
    skip_opt_in_local_config cni-bin-dir kubelet
    return 0
  fi

  return 1
}

fetch_as() {
  # download from location $1 to location $2
  if is_strict
  then
    ARCH="$($SNAP/bin/uname -m)"
    LD_LIBRARY_PATH="$SNAP/lib:$SNAP/usr/lib:$SNAP/lib/$ARCH-linux-gnu:$SNAP/usr/lib/$ARCH-linux-gnu" "${SNAP}/usr/bin/curl" -L $1 -o $2
  else
    CA_CERT=/snap/core20/current/etc/ssl/certs/ca-certificates.crt
    run_with_sudo "${SNAP}/usr/bin/curl" --cacert $CA_CERT -L $1 -o $2
  fi
}

############################# Strict functions ######################################

log_init () {
  echo `$SNAP/bin/date +"[%m-%d %H:%M:%S]" start logging` > $SNAP_COMMON/var/log/microk8s.log
}

log () {
  echo -n `$SNAP/bin/date +"[%m-%d %H:%M:%S]"` >> $SNAP_COMMON/var/log/microk8s.log
  echo ": $@" >> $SNAP_COMMON/var/log/microk8s.log
}

is_strict() {
  # Return 0 if we are in strict mode
  if $SNAP/bin/cat $SNAP/meta/snap.yaml | $SNAP/bin/grep confinement | $SNAP/bin/grep -q strict
  then
    return 0
  else
    return 1
  fi
}

check_snap_interfaces() {
    # Check whether all of the required interfaces are connected before proceeding.
    # This is to address https://forum.snapcraft.io/t/mimic-sequence-of-hook-calls-with-auto-connected-interfaces/19618
    declare -ra interfaces=(
        "account-control"
        "docker-privileged"
        "dot-kube"
        "dot-config-helm"
        "firewall-control"
        "hardware-observe"
        "home"
        "home-read-all"
        "k8s-journald"
        "k8s-kubelet"
        "k8s-kubeproxy"
        "kernel-module-observe"
        "kubernetes-support"
        "log-observe"
        "login-session-observe"
        "mount-observe"
        "network"
        "network-bind"
        "network-control"
        "network-observe"
        "opengl"
        "process-control"
        "system-observe"
    )

    declare -a missing=()

    for interface in ${interfaces[@]}
    do
        if ! snapctl is-connected ${interface}
        then
            missing+=("${interface}")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]
    then
        snapctl set-health blocked "You must connect ${missing[*]} before proceeding"
        exit 0
    fi
}

enable_snap() {
  snapctl start --enable ${SNAP_NAME}
  snapctl set-health okay
}

exit_if_not_root() {
  # test if we run with sudo
  if (is_strict) && [ "$EUID" -ne 0 ]
  then echo "Elevated permissions are needed for this command. Please use sudo."
    exit 1
  fi
}

is_first_boot_on_strict() {
  # Return 0 if this is the first start after the host booted.
  SENTINEL="/tmp/.containerd-first-book-check"
  # We rely on the fact that /tmp is cleared at every boot to determine if
  # this is the first call after boot: if the sentinel file exists, then it
  # means that no reboot occurred since last check; otherwise, return success
  # and create the sentinel file for the future check.
  if [ -f "$SENTINEL" ]
  then
    return 1
  else
    $SNAP/bin/touch "$SENTINEL"
    return 0
  fi
}

default_route_exists() {
  # test if we have a default route
  ( $SNAP/sbin/ip route; $SNAP/sbin/ip -6 route ) | $SNAP/bin/grep "^default" &>/dev/null
}

wait_for_default_route() {
  # wait 10 seconds for default route to appear
  n=0
  until [ $n -ge 5 ]
  do
    default_route_exists && break
    echo "Waiting for default route to appear. (attempt $n)"
    n=$[$n+1]
    sleep 2
  done
}

is_ec2_instance() {
  if [ -f "/sys/hypervisor/uuid" ]
  then
    EC2UID=$($SNAP/usr/bin/head -c 3 /sys/hypervisor/uuid | $SNAP/usr/bin/tr '[:upper:]' '[:lower:]')
    if [[ $EC2UID == *"ec2"* ]]
    then
      return 0
    fi
  else
    if [ -f "/sys/devices/virtual/dmi/id/product_uuid" ]
    then
      EC2UID=$($SNAP/usr/bin/head -c 3 /sys/devices/virtual/dmi/id/product_uuid | $SNAP/usr/bin/tr '[:upper:]' '[:lower:]')
      if [[ $EC2UID == *"ec2"* ]]
      then
        return 0
      fi
    fi
  fi
  return 1
}

increase_sysctl_parameter() {
  declare -a conf_locs=("/etc/sysctl.d/" "/run/sysctl.d/" "/usr/local/lib/sysctl.d/" "/usr/lib/sysctl.d/" "/lib/sysctl.d/" "/etc/sysctl.conf")

  local param_key=$1
  local new_val=$2

  val_max="0"

  if ! is_strict; then
    if [ -f "/etc/sysctl.d/10-microk8s.conf" ]; then
      run_with_sudo $SNAP/usr/bin/sort -u /etc/sysctl.d/10-microk8s.conf -o /etc/sysctl.d/10-microk8s.conf
    fi

    for loc in "${conf_locs[@]}"
    do
      if run_with_sudo $SNAP/bin/grep -qr "^$param_key=" $loc; then
        for val in $(run_with_sudo $SNAP/bin/grep -r "^$param_key=" $loc | $SNAP/bin/sed 's/^.*=//');
        do
          if [ "$val" -ge "$val_max" ]; then
            val_max=$val;
          fi
        done
      fi
    done

    if [ "$val_max" -lt "$new_val" ]; then
        echo "$param_key=$new_val" | run_with_sudo $SNAP/usr/bin/tee -a /etc/sysctl.d/10-microk8s.conf
        if ! run_with_sudo sysctl --system; then
          echo "Could not refresh system parameters via sysctl"
        fi
    fi
  fi
}

use_snap_env() {
  # Configure PATH, LD_LIBRARY_PATH and PYTHONPATH
  export PATH="$SNAP/usr/bin:$SNAP/bin:$SNAP/usr/sbin:$SNAP/sbin:$REAL_PATH"
  export LD_LIBRARY_PATH="$SNAP_LIBRARY_PATH:$SNAP/lib:$SNAP/usr/lib:$SNAP/lib/$SNAPCRAFT_ARCH_TRIPLET:$SNAP/usr/lib/$SNAPCRAFT_ARCH_TRIPLET:$SNAP/usr/lib/$SNAPCRAFT_ARCH_TRIPLET/ceph:${REAL_LD_LIBRARY_PATH:-}"
  export PYTHONPATH="$SNAP/usr/lib/python3.8:$SNAP/lib/python3.8/site-packages:$SNAP/usr/lib/python3/dist-packages"

  # Python configuration
  export PYTHONNOUSERSITE=false

  # NOTE(neoaggelos/2023-08-14):
  # we cannot list system locales from snap. instead, we attempt
  # well-known locales for Ubuntu/Debian/CentOS and check whether
  # they are available on the system.
  # if they are, set them for the current shell.
  for locale in C.UTF-8 en_US.UTF-8 en_US.utf8; do
    if [ -z "$(export LC_ALL=$locale 2>&1)" ]; then
      export LC_ALL="${LC_ALL:-$locale}"
      export LANG="${LC_ALL:-$locale}"
      break
    fi
  done

  # Configure XDG_RUNTIME_DIR
  export XDG_RUNTIME_DIR="${SNAP_COMMON}/run"
  mkdir -p "${XDG_RUNTIME_DIR}"
}

# check if this file is run with arguments
if [[ "$0" == "${BASH_SOURCE}" ]] &&
   [[ ! -z "$1" ]]
then
  # call help
  if echo "$*" | grep -q -- 'help'; then
    echo "usage: $0 [function]"
    echo ""
    echo "Run a utility function and return the output."
    echo ""
    echo "available functions:"
    declare -F | gawk '{print "- "$3}'
    exit 0
  fi

  if declare -F "$1" > /dev/null
  then
    $1 ${@:2}
    exit $?
  else
    echo "Function does not exist: $1" >&2
    exit 1
  fi
fi
