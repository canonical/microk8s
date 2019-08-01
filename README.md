# MicroK8s

![](https://img.shields.io/badge/Kubernetes-1.15-326de6.svg) ![Build Status](https://travis-ci.org/ubuntu/microk8s.svg?branch=master)

<img src="/docs/images/certified_kubernetes_color-222x300.png" align="right" width="200px">Kubernetes in a [snap](https://snapcraft.io/).

Dead simple to install, fully featured, always current with upstream Kubernetes available in 42 Linux distributions. Prefect for:

- workstations
- IoT devices
- Edge Computing
- CI/CD
- Cloud VMs (small clusters)

To quote [Kelsey Hightower](https://twitter.com/kelseyhightower/status/1120834594138406912), `... Canonical might have assembled the easiest way to provision a single node Kubernetes cluster`.

## How does it work?

- Being a [snap](https://snapcraft.io/microk8s), MicroK8s targets 42 Linux distributions.

- MicroK8s releases happen the same day as upstream K8s.

- Updates are seamlessly delivered keeping your cluster up-to-date.

- Dependencies are included in the 200MB snap package.

- All K8s versions from v1.10 onwards as well as alpha, beta and release candidates are available for testing your workload with.

- We maintain a curated collection of manifests for:
  - Service Mesh:  Istio, Linkerd
  - Serverless: Knative
  - Monitoring: Fluentd, Prometheus, Grafana, Metrics
  - Ingress, DNS, Dashboard, Clustering
  - Automatic updates to the latest Kubernetes version
  - GPGPU bindings for AI/ML
  - Kubeflow!

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

To use MicroK8s with your already installed kubectl, do this:

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

To contribute to the project have a look at the [build instruction](docs/build.md).

## Are you using MicroK8s?

Drop us a line at the "[MicroK8s In The Wild](docs/community.md)" page.


<p align="center">
  <img src="https://assets.ubuntu.com/v1/9309d097-MicroK8s_SnapStore_icon.svg" width="150px">
</p>
