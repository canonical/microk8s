# Building and testing MicroK8s

## Building the snap from source

To build the MicroK8s snap, you need to install Snapcraft.

```shell
sudo snap install snapcraft --classic
```

[Building a snap](https://snapcraft.io/docs/snapcraft-overview) is done by running `snapcraft` in the root of the project. Snapcraft spawn a VM managed by [Multipass](https://multipass.run/) and builds MicroK8s inside of it. If you don’t have Multipass installed, snapcraft will first prompt for its automatic installation.

After `snapcraft` finishes, you can install the newly compiled snap:

```shell
sudo snap install microk8s_*_amd64.snap --classic --dangerous
```

## Building the snap using LXD

Alternatively, you can build the snap in an LXC container. This is useful if you are working in a virtual machine without nested virtualization. Snapcraft and LXD are needed in this case:

```shell
sudo snap install lxd
sudo apt-get remove lxd* -y
sudo apt-get remove lxc* -y
sudo lxd init
sudo usermod -a -G lxd ${USER}
```

Build the snap with:

```shell
git clone http://github.com/ubuntu/microk8s
cd ./microk8s/
snapcraft --use-lxd
```

Finally, install it with:

```shell
sudo snap install microk8s_*_amd64.snap --classic --dangerous
```

## Building a custom MicroK8s package

To produce a custom build with specific component versions you cannot use the snapcraft build process on the host OS. You need to
[prepare an LXC](https://forum.snapcraft.io/t/how-to-create-a-lxd-container-for-snap-development/4658) container with Ubuntu 16:04 and snapcraft:

```shell
lxc launch ubuntu:16.04 --ephemeral test-build
lxc exec test-build -- snap install snapcraft --classic
lxc exec test-build -- apt update
lxc exec test-build -- git clone https://github.com/ubuntu/microk8s
```

You can then set the following environment variables prior to building:

- KUBE_VERSION: Kubernetes release to package. Defaults to latest stable.
- ETCD_VERSION: version of etcd.
- CNI_VERSION: version of CNI tools.
- KUBE_TRACK: Kubernetes release series (e.g., 1.10) to package. Defaults to latest stable.
- ISTIO_VERSION: istio release.
- KNATIVE_SERVING_VERSION: Knative Serving release.
- KNATIVE_EVENTING_VERSION: Knative Eventing release.
- RUNC_COMMIT: the commit hash from which to build runc.
- CONTAINERD_COMMIT: the commit hash from which to build containerd
- KUBERNETES_REPOSITORY: build the Kubernetes binaries from this repository instead of getting them from upstream
- KUBERNETES_COMMIT: commit to be used from KUBERNETES_REPOSITORY for building the Kubernetes binaries

For building you prepend the variables you need as well as `SNAPCRAFT_BUILD_ENVIRONMENT=host` so the current LXC container is used. For example to build the MicroK8s snap for Kubernetes v1.9.6, run:

```shell
lxc exec test-build -- sh -c "cd microk8s && SNAPCRAFT_BUILD_ENVIRONMENT=host KUBE_VERSION=v1.9.6 snapcraft"
```

The produced snap is inside the ephemeral LXC container, you need to copy it to the host:

```shell
lxc file pull test-build/root/microk8s/microk8s_v1.9.6_amd64.snap .
```

After copying it, you can install it with:

```shell
snap install microk8s_*_amd64.snap --classic --dangerous
```

## Assembling the Calico CNI manifest

The calico CNI manifest can be found under `upgrade-scripts/000-switch-to-calico/resources/calico.yaml`.
Building the manifest is subject to the upstream calico project k8s installation process.
At the time of the v3.13.2 release. The `calico.yaml` manifest is a slightly modified version of:
`https://docs.projectcalico.org/manifests/calico.yaml`:

- `CALICO_IPV4POOL_CIDR` was set to "10.1.0.0/16"
- `CNI_NET_DIR` was set to "/var/snap/microk8s/current/args/cni-network"
- We set the following mount paths:
  1. `var-run-calico` to `/var/snap/microk8s/current/var/run/calico`
  1. `var-lib-calico` to `/var/snap/microk8s/current/var/lib/calico`
  1. `cni-bin-dir` to `/var/snap/microk8s/current/opt/cni/bin`
  1. `cni-net-dir` to `/var/snap/microk8s/current/args/cni-network`
  1. `host-local-net-dir` to `/var/snap/microk8s/current/var/lib/cni/networks`
  1. `policysync` to `/var/snap/microk8s/current/var/run/nodeagent`
- We enabled vxlan following the instructions in [the official docs.](https://docs.projectcalico.org/getting-started/kubernetes/installation/config-options#switching-from-ip-in-ip-to-vxlan)
- `FELIX_LOGSEVERITYSCREEN` was set to "error"
- We set the IP autodetection method to

  ```dtd
              - name: IP_AUTODETECTION_METHOD
              value: "first-found"
  ```

## Running the tests locally

To successfully run the tests you need to install:

1. From your distribution's repository:
   - python3
   - pytest
   - pip3
   - docker.io
   - tox
1. From pip3:
   - requests
   - pyyaml
   - sh

On Ubuntu 20.04, for example, run the following commands to get these dependencies.

```shell
sudo apt install python3-pip docker.io tox -y
pip3 install -U pytest requests pyyaml sh
```

First, run the static analysis using Tox. Run the following command in the root of the project.

```shell
tox -e lint
```

Then, use the "Building the snap from source" instructions to build the snap and install it locally. The tests check this locally installed MicroK8s instance. 

Finally, run the tests themselves. The `test-addons.py` and `test-upgrade.py` files under the `tests` directory are the two main files of our test suite. Running the tests is done with pytest:

```shell
cd tests/
pytest -s test-addons.py
pytest -s test-upgrade.py
```
