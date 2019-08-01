# Building from source

To build the snap you need a [working LXD](https://linuxcontainers.org/lxd/getting-started-cli/#snap-package-archlinux-debian-fedora-opensuse-and-ubuntu) installation. To install LXD on Ubuntu first remove any old packages:
```
sudo apt-get purge lxc*
sudo apt-get purge lxd*
```

Get the latest LXD and configure it with:
```
sudo snap install lxd
lxd init --auto
```

Build MicroK8s with:
```
git clone https://github.com/ubuntu/microk8s
cd microk8s
snapcraft cleanbuild
```

## Building for specific versions

To produce a custome build with specific component versions we need to prepare an LXC container with Ubuntu 16:04 and snapcraft:
```
lxc launch ubuntu:16.04 --ephemeral test-build
lxc exec test-build -- snap install snapcraft --classic
lxc exec test-build -- apt update
lxc exec test-build -- git clone https://github.com/ubuntu/microk8s
```

We can then set the following environment variables prior to building:
 - KUBE_VERSION: kubernetes release to package. Defaults to latest stable.
 - ETCD_VERSION: version of etcd. Defaults to v3.3.4.
 - CNI_VERSION: version of CNI tools. Defaults to v0.7.1.
 - KUBE_TRACK: kubernetes release series (e.g., 1.10) to package. Defaults to latest stable.
 - ISTIO_VERSION: istio release. Defaults to v1.0.5.
 - KNATIVE_SERVING_VERSION: Knative Serving release. Defaults to v0.6.0.
 - KNATIVE_BUILD_VERSION: Knative Build release. Defaults to v0.5.0.
 - KNATIVE_EVENTING_VERSION: Knative Eventing release. Defaults to v0.5.0.
 - RUNC_COMMIT: the commit hash from which to build runc
 - CONTAINERD_COMMIT: the commit hash from which to build containerd

For building we use `snapcraft` (not `snapcraft cleanbuild`) and we prepend and variables we need. For example to build the MicroK8s snap for Kubernetes v1.9.6 we:
```
lxc exec test-build -- sh -c "cd microk8s && KUBE_VERSION=v1.9.6 snapcraft"
```

The produced snap is inside the ephemeral LXC container, we need to copy it to the host:
```
lxc file pull test-build/root/microk8s/microk8s_v1.9.6_amd64.snap .
```

## Installing the snap
```
snap install microk8s_latest_amd64.snap --classic --dangerous
```
