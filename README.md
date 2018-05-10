# microk8s

Kubernetes in a snap.

## Building the Snap
Building the snap is done with:
```
> snapcraft
```

You can set the following environment variables prior to building:
 - KUBE_VERSION: kubernetes release to package. Defaults to latest stable.
 - ETCD_VERSION: version of etcd. Defaults to v3.3.4.
 - CNI_VERSION: version of CNI tools. Defaults to v0.6.0.

For example:
```
> KUBE_VERSION=v1.9.6 snapcraft
```

To speed-up a build you can reuse the binaries already downloaded from a previous build. Binaries are placed under `parts/microk8s/build/build/kube_bins`. All you need to do is to make a copy of this directory and have the `KUBE_SNAP_BINS` environment variable point to it. Try this for example:
```
> snapcraft
... this build will take a long time and will download all binaries ...
> cp -r parts/microk8s/build/build/kube_bins .
> export KUBE_SNAP_BINS=$PWD/kube_bins/v1.10.2/
> snapcraft
... this build will be much faster and will reuse binaries in KUBE_SNAP_BINS

```

## Installing the Snap
```
snap install microk8s_v1.10.2_amd64.snap --devmode
```
