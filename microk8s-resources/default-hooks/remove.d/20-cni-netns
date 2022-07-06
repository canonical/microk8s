#!/bin/bash

. "${SNAP}/actions/common/utils.sh"

if ! is_strict || (is_strict && snapctl is-connected network-control)
then
  for ns in `"${SNAP}/sbin/ip" netns list | grep "^cni-" | awk '{print $1}'`
  do
    "${SNAP}/sbin/ip" netns delete "${ns}" || true
  done
fi
