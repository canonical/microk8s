#!/usr/bin/env bash

set -e

## remove an option inside the config file.
skip_opt_in_config() {
    opt="--$1"
    config_file="$SNAP_DATA/args/$2"
    sudo gawk -i inplace '!/^'"$opt"'/ {print $0}' "${config_file}"
}

# Apply the dns yaml
# We do not need to see dns pods running at this point just give some slack
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" "delete" "-f" "${SNAP}/actions/dns.yaml"
sleep 10

#TODO(kjackal): do not hardcode the info below. Get it from the yaml
skip_opt_in_config "cluster-domain" kubelet
skip_opt_in_config "cluster-dns" kubelet

sudo snapctl restart ${SNAP_NAME}.daemon-kubelet 2>&1 || true
