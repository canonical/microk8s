#!/bin/bash

. "${SNAP}/actions/common/utils.sh"

if ! is_strict || (is_strict && snapctl is-connected network-control)
then
  for link in cilium_host cilium_vxlan
  do
    if "${SNAP}/sbin/ip" link show "${link}"
    then
      "${SNAP}/sbin/ip" link delete "${link}" || true
    fi
  done
fi
