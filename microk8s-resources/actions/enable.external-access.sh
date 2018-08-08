#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Exposig microk8s to the default interface"

refresh_opt_in_config "insecure-bind-address" "0.0.0.0" kube-apiserver
sudo systemctl restart snap.${SNAP_NAME}.daemon-apiserver

echo "Kube API server accessible from the default interface"
