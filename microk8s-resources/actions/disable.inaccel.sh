#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Disabling InAccel FPGA Operator"

"$SNAP/microk8s-helm3.wrapper" uninstall inaccel

echo "InAccel is disabled"
