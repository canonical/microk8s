#!/bin/bash
lxc launch ubuntu:16.04 --ephemeral my-build
lxc exec my-build -- snap install snapcraft --classic
lxc exec my-build -- apt update
lxc exec my-build -- git clone https://github.com/ubuntu/microk8s.git
lxc exec my-build -- sh -c "cd microk8s && SNAPCRAFT_BUILD_ENVIRONMENT=host KUBE_VERSION=v1.15.7 snapcraft"
lxc file pull my-build/root/microk8s/microk8s_v1.15.7_amd64.snap .
