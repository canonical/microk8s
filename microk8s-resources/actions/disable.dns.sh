#!/usr/bin/env bash

set -e

skip_opt_in_config() {
    # remove an option inside the config file.
    # argument $1 is the option to be removed
    # argument $2 is the configuration file under $SNAP_DATA/args
    opt="--$1"
    config_file="$SNAP_DATA/args/$2"
    sudo "${SNAP}/bin/sed" -i '/'"$opt"'/d' "${config_file}"
}

echo "Disabling DNS"
echo "Reconfiguring kubelet"

skip_opt_in_config "cluster-domain" kubelet
skip_opt_in_config "cluster-dns" kubelet
sudo systemctl restart snap.${SNAP_NAME}.daemon-kubelet
sleep 5

# Apply the dns yaml
# We do not need to see dns pods running at this point just give some slack
echo "Removing DNS manifest"
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" "delete" "-f" "${SNAP}/actions/dns.yaml"

echo "DNS is disabled"
