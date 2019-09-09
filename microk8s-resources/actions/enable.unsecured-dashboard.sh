#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Applying manifest"
use_manifest unsecured-dashboard apply

echo "
Warning !!  Kubernertes unsecured dashboard only for DEV purposes !!
Dashboard can be accessed at http://127.0.0.1:30090
"

