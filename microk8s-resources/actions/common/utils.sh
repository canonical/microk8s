#!/usr/bin/env bash


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
    # Return the architecture we are on
    local ARCH="${KUBE_ARCH:-`dpkg --print-architecture`}"
    if [ "$ARCH" = "ppc64el" ]; then
        ARCH="ppc64le"
    elif [ "$ARCH" = "armhf" ]; then
        ARCH="arm"
    fi
    echo $ARCH
}


use_manifest() {
    local manifest="$1.yaml"
    local action="$2"
    local ARCH=$(arch)
    cat "${SNAP}/actions/${manifest}" | \
    "$SNAP/bin/sed" 's@\$ARCH@'"$ARCH"'@g' | \
    "$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" "$action" -f -
}
