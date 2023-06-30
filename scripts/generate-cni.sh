#!/bin/bash

set -x

source $SNAP/actions/common/utils.sh
if [ -e "${SNAP_DATA}/args/cni-env" ]; then
    source "${SNAP_DATA}/args/cni-env"
fi

CNI="${SNAP_DATA}/args/cni-network/cni.yaml"
RESOURCES="${SNAP}/upgrade-scripts/000-switch-to-calico/resources"
CLUSTER_CIDR=""
SERVICE_CIDR=""


function handle_ipv4 {
  # Update the cni.yaml with the IPv4 setup and update the cluster and service variables 
  sed -i '/"type": "calico-ipam"/i \              "assign_ipv4": "true",' "$CNI"
  if ! [[ -z "${IPv4_CLUSTER_CIDR}" ]] ; then
    sed -i 's%10.1.0.0/16%'"${IPv4_CLUSTER_CIDR}"'%g' "$CNI"
    CLUSTER_CIDR="${IPv4_CLUSTER_CIDR}"
  fi
  if ! [[ -z "${IPv4_SERVICE_CIDR}" ]] ; then
    SERVICE_CIDR="${IPv4_SERVICE_CIDR}"
  fi
}

function handle_ipv6 {
  # Update the cni.yaml with the IPv6 setup and update the cluster and service variables 

  sed -i '/"type": "calico-ipam"/i \              "assign_ipv6": "true",' "$CNI"
  sed -i '/FELIX_IPV6SUPPORT/{n;s/.*/\              value: "true"/}' "$CNI"
  sed -i '/CALICO_IPV6POOL_VXLAN/{n;s/.*/\              value: "Always"/}' "$CNI"
  sed -i '/Enable or Disable VXLAN on the default IPv6 IP pool./a \            - name: IP6' "$CNI"
  sed -i '/- name: IP6/a \              value: "autodetect"' "$CNI"
  if ! [[ -z "${IPv6_CLUSTER_CIDR}" ]] ; then
    sed -i '/Enable or Disable VXLAN on the default IPv6 IP pool./a \            - name: CALICO_IPV6POOL_CIDR' "$CNI"
    sed -i '/CALICO_IPV6POOL_CIDR/a \              value: '"${IPv6_CLUSTER_CIDR}" "$CNI"
    if [[ -z "${CLUSTER_CIDR}" ]]; then
      CLUSTER_CIDR="${IPv6_CLUSTER_CIDR}"
    else
      CLUSTER_CIDR="${CLUSTER_CIDR}","${IPv6_CLUSTER_CIDR}"
    fi
  fi
  if ! [[ -z "${IPv6_SERVICE_CIDR}" ]] ; then
    if [[ -z "${SERVICE_CIDR}" ]]; then
      SERVICE_CIDR="${IPv6_SERVICE_CIDR}"
    else
      SERVICE_CIDR="${SERVICE_CIDR}","${IPv6_SERVICE_CIDR}"
    fi
  fi
}

function setup_service_arguments {
  # Setup arguments in the microk8s services

  refresh_opt_in_local_config service-cluster-ip-range "${SERVICE_CIDR}" kube-controller-manager
  refresh_opt_in_local_config cluster-cidr "${CLUSTER_CIDR}" kube-controller-manager

  refresh_opt_in_local_config service-cluster-ip-range "${SERVICE_CIDR}" kube-apiserver

  refresh_opt_in_local_config cluster-cidr "${CLUSTER_CIDR}" kube-proxy
}


# Start with the default CNI and patch it based on the user needs
cp "${RESOURCES}/calico.yaml" "$CNI"
if ! [[ -z "${IPv4_SUPPORT}" ]] && [ "${IPv4_SUPPORT}" == "true" ]; then
  handle_ipv4
fi
if ! [[ -z "${IPv6_SUPPORT}" ]] && [ "${IPv6_SUPPORT}" == "true" ]; then
  handle_ipv6
fi
setup_service_arguments