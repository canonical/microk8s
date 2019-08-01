# MicroK8s

![](https://img.shields.io/badge/Kubernetes-1.15-326de6.svg) ![Build Status](https://travis-ci.org/ubuntu/microk8s.svg?branch=master)

<img src="/docs/images/certified_kubernetes_color-222x300.png" align="right" width="200px">Kubernetes in a [snap](https://snapcraft.io/microk8s).

Simple to install, full featured, always current Kubernetes available on 42 Linux distributions. Perfect for:

- Workstations
- IoT devices
- Edge Computing
- CI/CD
- Cloud VMs (small clusters)

To quote [Kelsey Hightower](https://twitter.com/kelseyhightower/status/1120834594138406912), `... Canonical might have assembled the easiest way to provision a single node Kubernetes cluster`.

## How does it work?

- A [snap](https://snapcraft.io/microk8s) package, MicroK8s runs on 42 different Linux distributions.

- MicroK8s releases happen the same day as upstream K8s.

- Updates are seamlessly delivered keeping your cluster up-to-date.

- Dependencies are included in the 200MB snap package.

- All K8s versions from v1.10 onwards as well as alpha, beta and release candidates are available.

- We maintain a curated collection of manifests for:
  - Service Mesh: Istio, Linkerd
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

To avoid colliding with an already-installed `kubectl`, and to avoid overwriting any existing Kubernetes configuration files, MicroK8s adds a `microk8s.kubectl` command, configured to exclusively access the MicroK8s cluster.

```
microk8s.kubectl get nodes
microk8s.kubectl get services
```

To instead use MicroK8s with an already-installed kubectl, do this:

```
microk8s.kubectl config view --raw > $HOME/.kube/config
```

#### Kubernetes add-ons

MicroK8s installs a barebones upstream Kubernetes. Additional services like dns and the Kubernetes dashboard can be enabled using the `microk8s.enable` command.

```
microk8s.enable dns dashboard
```

Use `microk8s.status` to see a list of enabled and available addons. You can find the addon manifests and/or scripts under `${SNAP}/actions/`, with `${SNAP}` pointing by default to `/snap/microk8s/current`.

## Documentation

For more information see the [official docs](https://microk8s.io/docs/).

To contribute to the project have a look at the [build instructions](docs/build.md).

## Are you using MicroK8s?

Drop us a line at the "[MicroK8s In The Wild](docs/community.md)" page.

<a href="https://snapcraft.io/microk8s" title="Get it from the Snap Store">
            <img src="https://snapcraft.io/static/images/badges/en/snap-store-white.svg" alt="Get it from the Snap Store" width="200" />
          </a>
