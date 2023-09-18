#!/usr/bin/env bash

set -x

source $SNAP/actions/common/utils.sh

use_snap_env

if [ -e "${SNAP_DATA}/args/cni-env" ]; then
    source "${SNAP_DATA}/args/cni-env"
fi

CNI_YAML="${SNAP_DATA}/args/cni-network/cni.yaml"
CALICO_RESOURCES="${SNAP}/upgrade-scripts/000-switch-to-calico/resources"

CLUSTER_CIDR=""
SERVICE_CIDR=""


function handle_calico {
  # Start with the default CNI and patch it based on the user needs
  cp "${CALICO_RESOURCES}/calico.yaml" "$CNI_YAML"

  # IPv4 configuration
  if test "x${IPv4_SUPPORT}" = "xtrue"; then
    # Update the calico cni.yaml with IPv4 specific configurations
    sed -i '/"type": "calico-ipam"/i \              "assign_ipv4": "true",' "$CNI_YAML"
    sed -i 's%10.1.0.0/16%'"${IPv4_CLUSTER_CIDR}"'%g' "$CNI_YAML"
  fi

  # IPv6 configuration
  if test "x${IPv6_SUPPORT}" = "xtrue"; then
    sed -i '/"type": "calico-ipam"/i \              "assign_ipv6": "true",' "$CNI_YAML"
    sed -i '/FELIX_IPV6SUPPORT/{n;s/.*/\              value: "true"/}' "$CNI_YAML"
    sed -i '/CALICO_IPV6POOL_VXLAN/{n;s/.*/\              value: "Always"/}' "$CNI_YAML"
    sed -i '/Enable or Disable VXLAN on the default IPv6 IP pool./a \            - name: IP6' "$CNI_YAML"
    sed -i '/- name: IP6/a \              value: "autodetect"' "$CNI_YAML"

    sed -i '/Enable or Disable VXLAN on the default IPv6 IP pool./a \            - name: CALICO_IPV6POOL_CIDR' "$CNI_YAML"
    sed -i '/CALICO_IPV6POOL_CIDR/a \              value: '"${IPv6_CLUSTER_CIDR}" "$CNI_YAML"

    sed -i '/Enable or Disable VXLAN on the default IPv6 IP pool./a \            - name: IP6_AUTODETECTION_METHOD' "$CNI_YAML"
    sed -i '/IP6_AUTODETECTION_METHOD/a \              value: "first-found"' "$CNI_YAML"
  fi

  # Other configuration
  if [ ! -z "${CALICO_VETH_MTU}" ]; then
    sed -i 's,veth_mtu: "0",veth_mtu: "'"${CALICO_VETH_MTU}"'",' "$CNI_YAML"
  fi
}


function validate_configuration {
  if test "x${IPv4_SUPPORT}" = "xtrue"; then
    if test "x${IPv4_CLUSTER_CIDR}" = "x"; then
      echo "Failed: IPv4_SUPPORT is true, but no IPv4_CLUSTER_CIDR was set"
      exit 1
    fi
    if test "x${IPv4_SERVICE_CIDR}" = "x"; then
      echo "Failed: IPv4_SUPPORT is true, but no IPv4_SERVICE_CIDR was set"
      exit 1
    fi
  fi

  if test "x${IPv6_SUPPORT}" = "xtrue"; then
    if test "x${IPv6_CLUSTER_CIDR}" = "x"; then
      echo "Failed: IPv6_SUPPORT is true, but no IPv6_CLUSTER_CIDR was set"
      exit 1
    fi
    if test "x${IPv6_SERVICE_CIDR}" = "x"; then
      echo "Failed: IPv6_SUPPORT is true, but no IPv6_SERVICE_CIDR was set"
      exit 1
    fi
  fi

  if test x"${IPv4_SUPPORT}" = "xtrue" && test x"${IPv6_SUPPORT}" = "xtrue"; then
    CLUSTER_CIDR="${IPv4_CLUSTER_CIDR},${IPv6_CLUSTER_CIDR}"
    SERVICE_CIDR="${IPv4_SERVICE_CIDR},${IPv6_SERVICE_CIDR}"
  elif test x"${IPv4_SUPPORT}" = "xtrue"; then
    CLUSTER_CIDR="${IPv4_CLUSTER_CIDR}"
    SERVICE_CIDR="${IPv4_SERVICE_CIDR}"
  elif test x"${IPv6_SUPPORT}" = "xtrue"; then
    CLUSTER_CIDR="${IPv6_CLUSTER_CIDR}"
    SERVICE_CIDR="${IPv6_SERVICE_CIDR}"
  else
    echo "Failed: At least one of IPv4_SUPPORT or IPv6_SUPPORT must be true"
    exit 1
  fi
}

function setup_service_arguments {
  # Setup arguments in the microk8s services

  refresh_opt_in_local_config service-cluster-ip-range "${SERVICE_CIDR}" kube-controller-manager
  refresh_opt_in_local_config cluster-cidr "${CLUSTER_CIDR}" kube-controller-manager

  refresh_opt_in_local_config service-cluster-ip-range "${SERVICE_CIDR}" kube-apiserver

  refresh_opt_in_local_config cluster-cidr "${CLUSTER_CIDR}" kube-proxy
}

# Common setup, validation and setup service arguments
validate_configuration
setup_service_arguments

# Do setup of the chosen CNI
case "${CNI}" in
  calico)
    handle_calico
    ;;
  *)
    echo "CNI must be set to 'calico'"
    exit 1
    ;;
esac
