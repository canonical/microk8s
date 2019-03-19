#!/bin/bash

set -ex

echo "--conntrack-max-per-core=0" >> /var/snap/microk8s/current/args/kube-proxy
systemctl restart snap.microk8s.daemon-proxy
