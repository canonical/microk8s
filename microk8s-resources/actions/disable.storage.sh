#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

"$SNAP/microk8s-disable.wrapper" hostpath-storage
