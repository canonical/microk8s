# Building the snap from source

[Building a snap](https://snapcraft.io/docs/snapcraft-overview) is done by running `snapcraft` on the root of the project.
A VM managed by Multipass is spawned to contain the build process. If you don’t have Multipass installed,
snapcraft will first prompt for its automatic installation.

Alternatively, you can build the snap in an LXC container.
LXD is needed in this case:
```
sudo snap install lxd
sudo apt-get remove lxd* -y
sudo apt-get remove lxc* -y
sudo lxd init
```

Build the snap with:
```
git clone http://github.com/ubuntu/microk8s
cd ./microk8s/
snapcraft --use-lxd
```

## Building a custom MicroK8s package

To produce a custom build with specific component versions we cannot use the snapcraft build process on the host OS. We need to
[prepare an LXC](https://forum.snapcraft.io/t/how-to-create-a-lxd-container-for-snap-development/4658)
container with Ubuntu 16:04 and snapcraft:
```
lxc launch ubuntu:16.04 --ephemeral test-build
lxc exec test-build -- snap install snapcraft --classic
lxc exec test-build -- apt update
lxc exec test-build -- git clone https://github.com/ubuntu/microk8s
```

We can then set the following environment variables prior to building:
 - KUBE_VERSION: kubernetes release to package. Defaults to latest stable.
 - ETCD_VERSION: version of etcd.
 - CNI_VERSION: version of CNI tools.
 - KUBE_TRACK: kubernetes release series (e.g., 1.10) to package. Defaults to latest stable.
 - ISTIO_VERSION: istio release.
 - KNATIVE_SERVING_VERSION: Knative Serving release.
 - KNATIVE_EVENTING_VERSION: Knative Eventing release.
 - RUNC_COMMIT: the commit hash from which to build runc
 - CONTAINERD_COMMIT: the commit hash from which to build containerd
 - KUBERNETES_REPOSITORY: build the kubernetes binaries from this repository instead of getting them from upstream
 - KUBERNETES_TAG: tag to be used from KUBERNETES_REPOSITORY for building the kubernetes banaries


For building we prepend the variables we need as well as `SNAPCRAFT_BUILD_ENVIRONMENT=host` so the current LXC container is used. For example to build the MicroK8s snap for Kubernetes v1.9.6 we:
```
lxc exec test-build -- sh -c "cd microk8s && SNAPCRAFT_BUILD_ENVIRONMENT=host KUBE_VERSION=v1.9.6 snapcraft"
```

The produced snap is inside the ephemeral LXC container, we need to copy it to the host:
```
lxc file pull test-build/root/microk8s/microk8s_v1.9.6_amd64.snap .
```

#### Installing the snap
```
snap install microk8s_latest_amd64.snap --classic --dangerous
```

## References

- https://snapcraft.io/docs/snapcraft-overview
- https://forum.snapcraft.io/t/how-to-create-a-lxd-container-for-snap-development/4658
