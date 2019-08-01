# MicroK8s

![](https://img.shields.io/badge/Kubernetes-1.15-326de6.svg) ![Build Status](https://travis-ci.org/ubuntu/microk8s.svg?branch=master)

<img src="/docs/images/certified_kubernetes_color-222x300.png" align="right" width="200px">Kubernetes in a [snap](https://snapcraft.io/).

Dead simple to install, fully featured, always fresh, upstream Kubernetes available in 42 Linux distributions. Prefect for:

- your workstation,
- CI/CD, and
- the edge

To quote [Kelsey Hightower](https://twitter.com/kelseyhightower/status/1120834594138406912), `... Canonical might have assembled the easiest way to provision a single node Kubernetes cluster`.

## How does it work?

- Being a [snap](https://snapcraft.io/microk8s), MicroK8s targets 42 Linux distributions.

- MicroK8s releases happen the same day as upstream K8s.

- Snap updates are seamlessly delivered keeping your cluster up-to-date.

- Dependencies are included in the 200MB snap package.

- All K8s versions from v1.10 onwards as well as alpha, beta and release candidates are available for testing your workload with.

- A curated collection of manifests is maintained for your convenience. You can enable DNS, dashboard, ingress, istio, knative in a single command.


## Quickstart

Deploy MicroK8s with:

```
snap install microk8s --classic
```

To avoid colliding with a `kubectl` already installed and to avoid overwriting any existing Kubernetes configuration file, MicroK8s adds a `microk8s.kubectl` command, configured to exclusively access the MicroK8s cluster. When following instructions online, make sure to prefix `kubectl` with `microk8s.`.

```
microk8s.kubectl get nodes
microk8s.kubectl get services
```

If you already have `kubectl` installed and you want to use it to access the MicroK8s deployment you can export the cluster's config with:

```
microk8s.kubectl config view --raw > $HOME/.kube/config
```

#### Kubernetes add-ons

MicroK8s installs a barebones upstream Kubernetes. Additional services like dns and dashboard can be run using the `microk8s.enable` command

```
microk8s.enable dns dashboard
```


With `microk8s.status` you can see the list of available addons and which ones are currently enabled. You can find the addon manifests and/or scripts under `${SNAP}/actions/`, with `${SNAP}` pointing by default to `/snap/microk8s/current`.

## Documentation

For more information see the [official docs](https://microk8s.io/docs/).


## Are you using MicroK8s?

Drop us a line at the "[MicroK8s In The Wild](docs/community.md)" page.


## Building the snap from source

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
 - ISTIO_VERSION: istio release. Defaults to v1.2.2.
 - KNATIVE_SERVING_VERSION: Knative Serving release. Defaults to v0.7.1.
 - KNATIVE_BUILD_VERSION: Knative Build release. Defaults to v0.7.0.
 - KNATIVE_EVENTING_VERSION: Knative Eventing release. Defaults to v0.7.1.
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

#### Installing the snap
```
snap install microk8s_latest_amd64.snap --classic --dangerous
```

<p align="center">
  <img src="https://assets.ubuntu.com/v1/9309d097-MicroK8s_SnapStore_icon.svg" width="150px">
</p>
