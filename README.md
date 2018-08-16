# microk8s

![](https://img.shields.io/badge/Kubernetes%20Conformance-139%2F140-green.svg) ![](https://img.shields.io/badge/Kubernetes-1.11-326de6.svg)

Kubernetes in a [snap](https://snapcraft.io/) that you can run locally.

## User Guide

Snaps are frequently updated to match each release of Kubernetes. The quickest way to get started is to install directly from the snap store

```
snap install microk8s --classic --beta
```

> At this time microk8s is an early beta, while this should be safe to install please beware.
> In order to install microk8s make sure port 8080 is not used.

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
If you already have `kubectl` installed and you want to use it to access the microk8s deployment you can export the cluster's config with:

```
microk8s.kubectl config view --raw > $HOME/.kube/config
```

Note: The API server on port 8080 is listening on all network interfaces. In its kubeconfig file microk8s is using the loopback interface, as you can see with `microk8s.kubectl config view`. The `microk8s.config` command will output a kubeconfig with the host machine's IP (instead of the 127.0.0.1) as the API server endpoint.


### Kubernetes Addons

microk8s installs a barebones upstream Kubernetes. This means just the api-server, controller-manager, scheduler, kubelet, cni, kube-proxy are installed and run. Additional services like kube-dns and dashboard can be run using the `microk8s.enable` command

```
microk8s.enable dns dashboard
```

These addons can be disabled at anytime using the `disable` command

```
microk8s.disable dashboard dns
```

You can find the addon manifests and/or scripts under `${SNAP}/actions/`, with `${SNAP}` pointing by default to `/snap/microk8s/current`.

#### List of available addons
- **dns**: Deploy kube dns. This addon may be required by others thus we recommend you always enable it.
- **dashboard**: Deploy kubernetes dashboard as well as grafana and influxdb. To access grafana point your browser to the url reported by `microk8s.kubectl cluster-info`.
- **storage**: Create a default storage class. This storage class makes use of the hostpath-provisioner pointing to a directory on the host. Persistent volumes are created under `${SNAP_COMMON}/default-storage`. Upon disabling this addon you will be asked if you want to delete the persistent volumes created.
- **ingress**: Create an ingress controller.
- **gpu**: Expose GPU(s) to microk8s by enabling the nvidia-docker runtime and nvidia-device-plugin-daemonset. Requires NVIDIA drivers to already be installed on the host system.
- **istio**: Deploy the core [Istio](https://istio.io/) services. You can use the `microk8s.istioctl` command to mange your deployments.
- **registry**: Deploy a docker private registry and expose it on `localhost:32000`. The storage addon will be enabled as part of this addon. To [use the registry](docs/registry.md) you can use the `microk8s.docker` command.

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

### Removing microk8s

Before removing microk8s, use `microk8s.reset` to stop all running pods.

```
microk8s.reset
snap remove microk8s
```

### Configuring microk8s services
The following systemd services will be running in your system:
- **snap.microk8s.daemon-apiserver**, is the [kube-apiserver](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-apiserver/) daemon started using the arguments in `${SNAP_DATA}/args/kube-apiserver`
- **snap.microk8s.daemon-controller-manager**, is the [kube-controller-manager](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-controller-manager/) daemon started using the arguments in `${SNAP_DATA}/args/kube-controller-manager`
- **snap.microk8s.daemon-scheduler**, is the [kube-scheduler](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-scheduler/) daemon started using the arguments in `${SNAP_DATA}/args/kube-scheduler`
- **snap.microk8s.daemon-kubelet**, is the [kubelet](https://kubernetes.io/docs/reference/command-line-tools-reference/kubelet/) daemon started using the arguments in `${SNAP_DATA}/args/kubelet`
- **snap.microk8s.daemon-proxy**, is the [kube-proxy](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-proxy/) daemon started using the arguments in `${SNAP_DATA}/args/kube-proxy`
- **snap.microk8s.daemon-docker**, is the [docker](https://docs.docker.com/engine/reference/commandline/dockerd/) daemon started using the arguments in `${SNAP_DATA}/args/dockerd`
- **snap.microk8s.daemon-etcd**, is the [etcd](https://coreos.com/etcd/docs/latest/v2/configuration.html) daemon started using the arguments in `${SNAP_DATA}/args/etcd`

Normally, `${SNAP_DATA}` points to `/var/snap/microk8s/current`.

To reconfigure a service you will need to edit the corresponding file and then restart the respective daemon. For example:
```
echo '--config-file=/path-to-my/daemon.json' | sudo tee -a /var/snap/microk8s/current/args/dockerd
sudo systemctl restart snap.microk8s.daemon-docker.service
```

## Troubleshooting

To troubleshoot a non-functional microk8s deployment, first ensure all daemons (listed above) are running. You can do that with `sudo systemctl status snap.microk8s.<daemon>`. If you see a stopped service you can examine its logs with `journalctl -u snap.microk8s.<daemon>.service`. We'll probably ask you for these logs when you open an [issue](https://github.com/ubuntu/microk8s/issues).

Some common problems and solutions are listed below.

### My dns and dashboard pods are CrashLooping.
The [Kubenet](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/) network plugin used by microk8s creates a `cbr0` interface when the first pod is created. If you have `ufw` enabled, you'll need to allow traffic on this interface:

`sudo ufw allow in on cbr0 && sudo ufw allow out on cbr0`

### My pods can't reach the internet (but my microk8s host machine can).
Make sure packets to/from the pod network interface can be forwarded
to/from the default interface on the host:

`sudo iptables -P FORWARD ACCEPT`

or, if using `ufw`:

`sudo ufw default allow routed`

### My host machine changed IP and now microk8s is not working properly.
The host machine IP may change whenever you switch places with your laptop or you go through a suspend/resume cycle. The kubernetes API server advertises this IP (taken from the default interface) to all kubernetes cluster members. Services such as DNS and the dashboard will lose connectivity to API server in case the host IP changes. You will need to restart microk8s whenever this happens:
```
sudo snap disable microk8s
sudo snap enable microk8s
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
 - CNI_VERSION: version of CNI tools. Defaults to v0.7.1.
 - KUBE_TRACK: kubernetes release series (e.g., 1.10) to package. Defaults to latest stable.
 - ISTIO_VERSION: istio release. Defaults to v1.0.0.

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
> export KUBE_SNAP_BINS=$PWD/kube_bins/v1.10.3/
> snapcraft
... this build will be much faster and will reuse binaries in KUBE_SNAP_BINS

```

### Installing the snap
```
snap install microk8s_v1.10.3_amd64.snap --classic --dangerous
```
