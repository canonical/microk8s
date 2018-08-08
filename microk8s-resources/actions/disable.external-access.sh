#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Restricting microk8s access to localhost"

refresh_opt_in_config "insecure-bind-address" "127.0.0.1" kube-apiserver
sudo systemctl restart snap.${SNAP_NAME}.daemon-apiserver

echo "Kube API server accessible only from localhost"
