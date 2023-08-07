#!/bin/bash

. "${SNAP}/actions/common/utils.sh"

if ! is_strict || (is_strict && snapctl is-connected network-control)
then
  for link in cni0
  do
    if "${SNAP}/sbin/ip" link show "${link}"
    then
      "${SNAP}/sbin/ip" link delete "${link}" || true
    fi
  done
  for calink in $("${SNAP}/sbin/ip" -j link show |\
                  "${SNAP}/usr/bin/jq" -r '.[].ifname | select(test("^vxlan[-v6]*.calico|cali[a-f0-9]*$"))')
  do "${SNAP}/sbin/ip" link delete "${calink}" || true
  done
fi
