#!/usr/bin/env bash

set -eu

source $SNAP/actions/common/utils.sh

function get_juju_client () {
  # check if juju cli is already in the system.  Download if it doesn't exist.
  if [ ! -f "${SNAP_DATA}/bin/juju" ]; then
    JUJU_VERSION="${JUJU_VERSION:-2.7.0}"
    JUJU_SERIES=$(echo $JUJU_VERSION | sed 's|\.[0-9]\+$||')

    run_with_sudo mkdir -p "$SNAP_DATA/bin"
    run_with_sudo mkdir -p "$SNAP_DATA/tmp"
    run_with_sudo "${SNAP}/usr/bin/curl" -L https://launchpad.net/juju/$JUJU_SERIES/$JUJU_VERSION/+download/juju-$JUJU_VERSION-centos7.tar.gz -o "$SNAP_DATA/tmp/juju.tar.gz"
    run_with_sudo "${SNAP}/bin/tar" -zxvf "$SNAP_DATA/tmp/juju.tar.gz" -C "$SNAP_DATA/tmp"
    run_with_sudo tar -zxvf "$SNAP_DATA/tmp/juju.tar.gz" -C "$SNAP_DATA/tmp"
    run_with_sudo cp "$SNAP_DATA/tmp/juju-bin/juju" "$SNAP_DATA/bin"
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
