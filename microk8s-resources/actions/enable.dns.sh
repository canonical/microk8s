#!/usr/bin/env bash

set -e

## add or replace an option inside the config file. Create the file if doesn't exist
refresh_opt_in_config() {
    opt="--$1"
    value="$2"
    config_file="$SNAP_DATA/args/$3"
    replace_line="$opt=$value"
    if $(grep -qE "^$opt=" $config_file); then
        sudo sed -i "s/^$opt=.*/$replace_line/" $config_file
    else
        sudo sed -i "$ a $replace_line" "$config_file"
    fi
}

# Apply the dns yaml
# We do not need to see dns pods running at this point just give some slack
echo "Enabling DNS"
echo "Applying manifest"
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" "apply" "-f" "${SNAP}/actions/dns.yaml"
sleep 5

echo "Restarting kubelet"
#TODO(kjackal): do not hardcode the info below. Get it from the yaml
refresh_opt_in_config "cluster-domain" "cluster.local" kubelet
refresh_opt_in_config "cluster-dns" "10.152.183.10" kubelet

sudo systemctl restart snap.${SNAP_NAME}.daemon-kubelet
echo "DNS is enabled"
