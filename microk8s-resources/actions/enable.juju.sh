#!/usr/bin/env bash

set -eu

source $SNAP/actions/common/utils.sh


function get_juju_client () {
  # check if juju cli is already in the system.  Download if it doesn't exist.
  if [ ! -f "${SNAP_DATA}/bin/juju" ]; then
    run_with_sudo mkdir -p "$SNAP_DATA/bin"
    run_with_sudo mkdir -p "$SNAP_DATA/tmp"
    run_with_sudo snap download juju --channel edge --target-directory="$SNAP_DATA/tmp"
    run_with_sudo "$SNAP/usr/bin/unsquashfs" -d "$SNAP_DATA/tmp/juju" $SNAP_DATA/tmp/juju_*.snap bin/juju
    run_with_sudo cp "$SNAP_DATA/tmp/juju/bin/juju" "$SNAP_DATA/bin"
    # TODO: Re-enable this method when 2.7 hits stable
#    sudo "${SNAP}/usr/bin/curl" -L https://launchpad.net/juju/2.6/2.6.4/+download/juju-2.6.4-centos7.tar.gz -o "$SNAP_DATA/tmp/juju.tar.gz"
#    #sudo "${SNAP}/bin/tar" -zxvf "$SNAP_DATA/tmp/juju.tar.gz" -C "$SNAP_DATA/tmp"
#    sudo tar -zxvf "$SNAP_DATA/tmp/juju.tar.gz" -C "$SNAP_DATA/tmp"
#    sudo cp "$SNAP_DATA/tmp/juju-bin/juju" "$SNAP_DATA/bin"
    run_with_sudo chmod uo+x "$SNAP_DATA/bin/juju"
    run_with_sudo mkdir -p "$SNAP_DATA/juju/share/juju" "$SNAP_DATA/juju-home"
    run_with_sudo chmod -R ug+rwX "$SNAP_DATA/juju/share/juju" "$SNAP_DATA/juju-home"
    run_with_sudo chmod -R o-rwX "$SNAP_DATA/juju/share/juju" "$SNAP_DATA/juju-home"

    if getent group microk8s >/dev/null 2>&1
    then
      run_with_sudo chgrp microk8s -R "$SNAP_DATA/juju/share/juju" "$SNAP_DATA/juju-home" || true
    fi

    run_with_sudo rm -rf "$SNAP_DATA/tmp/"
  fi
}


echo "Installing Juju"
get_juju_client
echo "Read more about juju at https://docs.jujucharms.com/"
