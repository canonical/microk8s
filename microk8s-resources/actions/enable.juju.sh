#!/usr/bin/env bash

set -eu

source $SNAP/actions/common/utils.sh


function get_juju_client () {
  # check if juju cli is already in the system.  Download if it doesn't exist.
  if [ ! -f "${SNAP_DATA}/bin/juju" ]; then
    sudo mkdir -p "$SNAP_DATA/bin"
    sudo mkdir -p "$SNAP_DATA/tmp"
    sudo snap download juju --channel edge --target-directory="$SNAP_DATA/tmp"
    sudo unsquashfs -d "$SNAP_DATA/tmp/juju" $SNAP_DATA/tmp/juju_*.snap bin/juju
    sudo cp "$SNAP_DATA/tmp/juju/bin/juju" "$SNAP_DATA/bin"
    # TODO: Re-enable this method when 2.7 hits stable
#    sudo "${SNAP}/usr/bin/curl" -L https://launchpad.net/juju/2.6/2.6.4/+download/juju-2.6.4-centos7.tar.gz -o "$SNAP_DATA/tmp/juju.tar.gz"
#    #sudo "${SNAP}/bin/tar" -zxvf "$SNAP_DATA/tmp/juju.tar.gz" -C "$SNAP_DATA/tmp"
#    sudo tar -zxvf "$SNAP_DATA/tmp/juju.tar.gz" -C "$SNAP_DATA/tmp"
#    sudo cp "$SNAP_DATA/tmp/juju-bin/juju" "$SNAP_DATA/bin"
    sudo chmod uo+x "$SNAP_DATA/bin/juju"
    sudo rm -rf "$SNAP_DATA/tmp/"
  fi
}


echo "Installing Juju"
get_juju_client
echo "Read more about juju at https://docs.jujucharms.com/"
