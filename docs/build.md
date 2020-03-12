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
 - CNI_VERSION: version of CNI tools.
 - KUBE_TRACK: kubernetes release series (e.g., 1.10) to package. Defaults to latest stable.
 - ISTIO_VERSION: istio release.
 - KNATIVE_SERVING_VERSION: Knative Serving release.
 - KNATIVE_EVENTING_VERSION: Knative Eventing release.
 - RUNC_COMMIT: the commit hash from which to build runc
 - CONTAINERD_COMMIT: the commit hash from which to build containerd
 - KUBERNETES_REPOSITORY: build the kubernetes binaries from this repository instead of getting them from upstream


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

## Compiling the Cilium CNI manifest

The cilium CNI manifest can be found at runtime under `$SNAP_DATA/args/cni-network/cilium.yaml` and
in the source tree along with the rest of the `default-args`. Building the manifest is subject to
the upstream cilium project k8s installation process. At the time of the v1.7 release the following script was used to place the
cilium manifest under `$SNAP_DATA/args/cni-network/cilium.yaml`:

```
#!/bin/bash

set -x

SNAP_DATA="/var/snap/microk8s/current"
SNAP_COMMON="/var/snap/microk8s/common"

CILIUM_VERSION="v1.7"
CILIUM_ERSION=$(echo $CILIUM_VERSION | sed 's/v//g')
SOURCE_URI="https://github.com/cilium/cilium/archive"
CILIUM_DIR="cilium-$CILIUM_ERSION"
CILIUM_CNI_CONF="plugins/cilium-cni/05-cilium-cni.conf"
CILIUM_LABELS="k8s-app=cilium"
NAMESPACE=kube-system

mkdir -p /tmp/cilium
cd /tmp/cilium
curl -L $SOURCE_URI/$CILIUM_VERSION.tar.gz -o "/tmp/cilium/cilium.tar.gz"
gzip -f -d /tmp/cilium/cilium.tar.gz
tar -xf /tmp/cilium/cilium.tar "$CILIUM_DIR/install" "$CILIUM_DIR/$CILIUM_CNI_CONF"
cp /tmp/cilium/$CILIUM_DIR/$CILIUM_CNI_CONF "$SNAP_DATA/args/cni-network/05-cilium-cni.conf"

cd "/tmp/cilium/$CILIUM_DIR/install/kubernetes"
helm template cilium \
   --namespace $NAMESPACE \
   --set global.cni.confPath="$SNAP_DATA/args/cni-network" \
   --set global.cni.binPath="$SNAP_DATA/opt/cni/bin" \
   --set global.cni.customConf=true \
   --set global.containerRuntime.integration="containerd" \
   --set global.containerRuntime.socketPath="$SNAP_COMMON/run/containerd.sock" > $SNAP_DATA/args/cni-network/cilium.yaml

sed -i 's;path: \(/var/run/cilium\);path: '"$SNAP_DATA"'\1;g' "$SNAP_DATA/args/cni-network/cilium.yaml"
```
  

## References

- https://snapcraft.io/docs/snapcraft-overview
- https://forum.snapcraft.io/t/how-to-create-a-lxd-container-for-snap-development/4658
