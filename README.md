# MicroK8s

![](https://img.shields.io/badge/Kubernetes-1.13-326de6.svg) ![Build Status](https://travis-ci.org/ubuntu/microk8s.svg)

<img src="https://raw.githubusercontent.com/cncf/artwork/master/kubernetes/certified-kubernetes/versionless/color/certified-kubernetes-color.png" align="right" width="200px">Kubernetes in a [snap](https://snapcraft.io/) that you can run locally.

## User Guide

Snaps are frequently updated to match each release of Kubernetes. The quickest way to get started is to install directly from the snap store. You can install MicroK8s and let it update to the latest stable upstream Kubernetes release with:

```
snap install microk8s --classic
```

Alternatively, you can select a MicroK8s channel that will follow a specific Kubernetes release series. For example, you install MicroK8s and let it follow the `v1.12` series with:

```
snap install microk8s --classic --channel=1.12/stable
```

You can read more on the MicroK8s release channels in the [Release Channels and Upgrades](docs/release-channels.md) doc.

At any point you can check MicroK8s' availability with:

```
microk8s.status
```

During installation you can use the `--wait-ready` flag to wait for the kubernetes services to initialise:

```
microk8s.status --wait-ready
```

> In order to install MicroK8s make sure
> - port 8080 is not used and
> - if you have AppArmor enabled (check with `sudo apparmor_status`) you do not have any other [dockerd installed](docs/dockerd.md). You can use the dockerd coming with MicroK8s.

### Accessing Kubernetes

To avoid colliding with a `kubectl` already installed and to avoid overwriting any existing Kubernetes configuration file, MicroK8s adds a `microk8s.kubectl` command, configured to exclusively access the new MicroK8s install. When following instructions online, make sure to prefix `kubectl` with `microk8s.`.

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
If you already have `kubectl` installed and you want to use it to access the MicroK8s deployment you can export the cluster's config with:

```
microk8s.kubectl config view --raw > $HOME/.kube/config
```

Note: The API server on port 8080 is listening on all network interfaces. In its kubeconfig file MicroK8s is using the loopback interface, as you can see with `microk8s.kubectl config view`. The `microk8s.config` command will output a kubeconfig with the host machine's IP (instead of the 127.0.0.1) as the API server endpoint.


### Kubernetes Addons

MicroK8s installs a barebones upstream Kubernetes. This means just the api-server, controller-manager, scheduler, kubelet, cni, kube-proxy are installed and run. Additional services like kube-dns and dashboard can be run using the `microk8s.enable` command

```
microk8s.enable dns dashboard
```

These addons can be disabled at anytime using the `disable` command

```
microk8s.disable dashboard dns
```

With `microk8s.status` you can see the list of available addons and which ones are currently enabled. You can find the addon manifests and/or scripts under `${SNAP}/actions/`, with `${SNAP}` pointing by default to `/snap/microk8s/current`.

#### List of Available Addons
- **dns**: Deploy kube dns. This addon may be required by others thus we recommend you always enable it.
- **dashboard**: Deploy kubernetes dashboard as well as grafana and influxdb. To access grafana point your browser to the url reported by `microk8s.kubectl cluster-info`.
- **storage**: Create a default storage class. This storage class makes use of the hostpath-provisioner pointing to a directory on the host. Persistent volumes are created under `${SNAP_COMMON}/default-storage`. Upon disabling this addon you will be asked if you want to delete the persistent volumes created.
- **ingress**: Create an ingress controller.
- **gpu**: Expose GPU(s) to MicroK8s by enabling the nvidia-docker runtime and nvidia-device-plugin-daemonset. Requires NVIDIA drivers to already be installed on the host system.
- **istio**: Deploy the core [Istio](https://istio.io/) services. You can use the `microk8s.istioctl` command to manage your deployments.
- **registry**: Deploy a docker private registry and expose it on `localhost:32000`. The storage addon will be enabled as part of this addon. To [use the registry](docs/registry.md) you can use the `microk8s.docker` command.
- **metrics-server**: Deploy the [Metrics Server](https://kubernetes.io/docs/tasks/debug-application-cluster/core-metrics-pipeline/#metrics-server).

### Stopping and Restarting MicroK8s

You may wish to temporarily shutdown MicroK8s when not in use without un-installing it.

MicroK8s can be shutdown with:

```
microk8s.stop
```

MicroK8s can be restarted later with:

```
microk8s.start
```

### Removing MicroK8s

Before removing MicroK8s, use `microk8s.reset` to stop all running pods.

```
microk8s.reset
snap remove microk8s
```

### Configuring MicroK8s Services
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

### Deploy Behind a Proxy

To let MicroK8s use a proxy enter the proxy details in `${SNAP_DATA}/args/dockerd-env` and restart the docker daemon service with:
```
sudo systemctl restart snap.microk8s.daemon-docker.service
```


## Troubleshooting

To troubleshoot a non-functional MicroK8s deployment, start by running the `microk8s.inspect` command. This command performs a set of tests against MicroK8s and collects traces and logs in a report tarball. In case any of the aforementioned daemons are failing you will be urged to look at the respective logs with `journalctl -u snap.microk8s.<daemon>.service`. `microk8s.inspect` may also make suggestions on potential issues it may find. If you do not manage to resolve the issue you are facing please file a [bug](https://github.com/ubuntu/microk8s/issues) attaching the inspection report tarball.

Some common problems and solutions are listed below.

### My dns and dashboard pods are CrashLooping.
The [Kubenet](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/) network plugin used by MicroK8s creates a `cbr0` interface when the first pod is created. If you have `ufw` enabled, you'll need to allow traffic on this interface:

`sudo ufw allow in on cbr0 && sudo ufw allow out on cbr0`

### My pods can't reach the internet or each other (but my MicroK8s host machine can).
Make sure packets to/from the pod network interface can be forwarded
to/from the default interface on the host:

`sudo iptables -P FORWARD ACCEPT`

or, if using `ufw`:

`sudo ufw default allow routed`

The microk8s inspect command can be used to check the firewall configuration:

`microk8s.inspect`

A warning will be shown if the firewall is not forwarding traffic.

### My host machine changed IP and now MicroK8s is not working properly.
The host machine IP may change whenever you switch places with your laptop or you go through a suspend/resume cycle. The kubernetes API server advertises this IP (taken from the default interface) to all kubernetes cluster members. Services such as DNS and the dashboard will lose connectivity to API server in case the host IP changes. You will need to restart MicroK8s whenever this happens:
```
microk8s.stop
microk8s.start
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
> snapcraft clean
> snapcraft
... this build will be much faster and will reuse binaries in KUBE_SNAP_BINS

```

### Installing the snap
```
snap install microk8s_v1.10.3_amd64.snap --classic --dangerous
```

<p align="center">
  <img src="https://assets.ubuntu.com/v1/9309d097-MicroK8s_SnapStore_icon.svg" width="150px">
</p>
