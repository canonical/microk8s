#!/usr/bin/env bash

# test-airgap.sh is called from test-distro.sh

airgap_wait_for_pods() {
  container="$1"

  lxc exec $container -- bash -c "
    while ! microk8s kubectl wait -n kube-system ds/calico-node --for=jsonpath='{.status.numberReady}'=1; do
      echo waiting for calico
      sleep 3
    done

    while ! microk8s kubectl wait -n kube-system deploy/hostpath-provisioner --for=jsonpath='{.status.readyReplicas}'=1; do
      echo waiting for hostpath provisioner
      sleep 3
    done

    while ! microk8s kubectl wait -n kube-system deploy/coredns --for=jsonpath='{.status.readyReplicas}'=1; do
      echo waiting for coredns
      sleep 3
    done
  "
}

function setup_airgap_registry_mirror() {
  create_machine "airgap-registry" $PROXY
  if [[ ${TO_CHANNEL} =~ /.*/microk8s.*snap ]]
  then
    lxc file push ${TO_CHANNEL} airgap-registry/tmp/microk8s_latest_amd64.snap
    lxc exec airgap-registry -- snap install /tmp/microk8s_latest_amd64.snap --dangerous --classic
  else
    lxc exec airgap-registry -- snap install microk8s --channel=${TO_CHANNEL} --classic
  fi
}

function setup_airgap_registry_addons() {
  lxc exec airgap-registry -- microk8s enable registry storage dns
}

function wait_airgap_registry() {
  airgap_wait_for_pods airgap-registry
  lxc exec airgap-registry -- bash -c '
    while ! curl --silent 127.0.0.1:32000/v2/_catalog; do
      echo waiting for registry
      sleep 2
    done
  '
}

function push_images_to_registry() {
  lxc exec airgap-registry -- bash -c '
    for image in $(microk8s ctr image ls -q | grep -v "sha256:"); do
      mirror=$(echo $image | sed '"'s,\(docker.io\|k8s.gcr.io\|registry.k8s.io\|quay.io\),airgap-registry:32000,g'"')
      sudo microk8s ctr image convert ${image} ${mirror}
      sudo microk8s ctr image push ${mirror} --plain-http
    done
  '
}

function setup_airgapped_microk8s() {
  create_machine "airgap-test" $PROXY
  if [[ ${TO_CHANNEL} =~ /.*/microk8s.*snap ]]
  then
    lxc file push ${TO_CHANNEL} airgap-test/tmp/microk8s.snap
  else
    lxc exec airgap-test -- snap download microk8s --channel=${TO_CHANNEL} --target-directory /tmp --basename microk8s
  fi
  lxc exec airgap-test -- bash -c "
    snap install core20
    snap install snapd
    echo '
  network:
    version: 2
    ethernets:
      eth0:
        dhcp4-overrides: { use-routes: false }
        routes: [{ to: 0.0.0.0/0, scope: link }]
  ' > /etc/netplan/70-airgap.yaml
    netplan apply
  "
  if lxc exec airgap-test -- bash -c "ping -c1 1.1.1.1"; then
    echo "machine for airgap test has internet access when it should not"
    exit 1
  fi
  lxc exec airgap-test -- snap install /tmp/microk8s.snap --dangerous --classic
}

function configure_airgapped_microk8s_mirrors() {
  lxc exec airgap-test -- bash -c '
    echo "
      server = \"http://airgap-registry:32000\"

      [host.\"http://airgap-registry:32000\"]
        capabilities = [\"pull\", \"resolve\"]
    " > hosts.toml

    for registry in registry.k8s.io k8s.gcr.io docker.io quay.io; do
      mkdir -p /var/snap/microk8s/current/args/certs.d/$registry
      cp hosts.toml /var/snap/microk8s/current/args/certs.d/$registry/hosts.toml
    done

    sudo snap restart microk8s.daemon-containerd
  '
}

function test_airgapped_microk8s() {
  lxc exec airgap-test -- bash -c 'sudo microk8s enable hostpath-storage dns'
  airgap_wait_for_pods airgap-test

}

function post_airgap_tests() {
  lxc rm airgap-registry --force
  lxc rm airgap-test --force
}
