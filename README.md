# microk8s

![](https://img.shields.io/badge/Kubernetes%20Conformance-139%2F140-green.svg) ![](https://img.shields.io/badge/Kubernetes-1.10-326de6.svg)

Kubernetes in a [snap](https://snapcraft.io/) that you can run locally.

## User Guide

Snaps are frequently updated to match each release of Kubernetes. The quickest way to get started is to install directly from the snap store

```
snap install microk8s --classic --beta
```

> At this time microk8s is an early beta, while this should be safe to install please beware.
> In order to install microk8s, make sure any current docker daemons are stopped and port 8080 is unused.

### Accessing Kubernetes

To avoid colliding with a `kubectl` already installed and to avoid overwriting any existing Kubernetes configuration file, microk8s adds a `microk8s.kubectl` command, configured to exclusively access the new microk8s install. When following instructions online, make sure to prefix `kubectl` with `microk8s.`.

```
microk8s.kubectl get nodes
microk8s.kubectl get services
```

If you do not already have a `kubectl` installed you can alias `microk8s.kubectl` to `kubectl` using the following command

```
snap alias microk8s.kubectl kubectl
```

This measure can be safely reverted at anytime by doing

```
snap unalias kubectl
```

### Kubernetes Addons

microk8s installs a barebones upstream Kubernetes. This means just the api-server, controller-manager, scheduler, kubelet, cni, kube-proxy are installed and run. Additional services like kube-dns and dashboard can be run using the `microk8s.enable` command

```
microk8s.enable dns dashboard
```

These addons can be disabled at anytime using the `disable` command

```
microk8s.disable dashboard dns
```

### Stopping and Restarting microk8s

You may wish to temporarily shutdown microk8s when not in use without un-installing it.

microk8s can be shutdown using the snap command

```
snap disable microk8s
```

microk8s can be restarted later with the snap command

```
snap enable microk8s
```




## Building from source

Build the snap with:
```
snapcraft
```

### Building for specific versions

You can set the following environment variables prior to building:
 - KUBE_VERSION: kubernetes release to package. Defaults to latest stable.
 - ETCD_VERSION: version of etcd. Defaults to v3.3.4.
 - CNI_VERSION: version of CNI tools. Defaults to v0.6.0.

For example:
```
KUBE_VERSION=v1.9.6 snapcraft
```

### Faster builds

To speed-up a build you can reuse the binaries already downloaded from a previous build. Binaries are placed under `parts/microk8s/build/build/kube_bins`. All you need to do is to make a copy of this directory and have the `KUBE_SNAP_BINS` environment variable point to it. Try this for example:
```
> snapcraft
... this build will take a long time and will download all binaries ...
> cp -r parts/microk8s/build/build/kube_bins .
> export KUBE_SNAP_BINS=$PWD/kube_bins/v1.10.2/
> snapcraft
... this build will be much faster and will reuse binaries in KUBE_SNAP_BINS

```

### Installing the snap
```
snap install microk8s_v1.10.3_amd64.snap --classic --dangerous
```
