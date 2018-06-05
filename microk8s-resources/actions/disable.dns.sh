#!/usr/bin/env bash

set -e

## remove an option inside the config file.
skip_opt_in_config() {
    opt="--$1"
    config_file="$SNAP_DATA/args/$2"
    sudo AWKLIBPATH="${SNAP}/usr/lib/x86_64-linux-gnu/gawk" AWKPATH="${SNAP}/usr/share/awk/" \
      "${SNAP}/usr/bin/gawk" -i inplace '!/^'"$opt"'/ {print $0}' "${config_file}"
}

echo "Disabling DNS"
echo "Reconfiguring kubelet"
#TODO(kjackal): do not hardcode the info below. Get it from the yaml
skip_opt_in_config "cluster-domain" kubelet
skip_opt_in_config "cluster-dns" kubelet
sudo systemctl restart snap.${SNAP_NAME}.daemon-kubelet
sleep 5

# Apply the dns yaml
# We do not need to see dns pods running at this point just give some slack
echo "Removing DNS manifest"
"$SNAP/kubectl" "--kubeconfig=$SNAP/client.config" "delete" "-f" "${SNAP}/actions/dns.yaml"

echo "DNS is disabled"
