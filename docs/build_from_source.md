# Building from source

Building a new version of MicroK8s from the source is straightforward.

1.  If you don't already have it, install the latest version of the `snapcraft` tool:
     ```bash
     sudo snap install snapcraft --classic
     ```
1. Clone the MicroK8s repository:
     ```bash
     git clone https://github.com/ubuntu/microk8s.git
     cd microk8s/
     ```
1. Ensure local package lists are up to date. On Ubuntu, run:
     ```bash
     sudo apt update
     ```
1. Run snapcraft to build the snap package:
     ```bash
     snapcraft
     ```
1. Once the snap is built it can be installed with:
     ```bash
     snap install microk8s_v1.12.2_amd64.snap --classic --dangerous
     ```
     (substitute the name of the version that was actually built as required).

For more information on managing snaps, see the [Snapcraft documentation](https://docs.snapcraft.io/getting-started/3876)


## Using different build options

You can set the following environment variables prior to building:

| Variable                 | Description                                                    | Default value                     |
|--------------------------|-----------------------------------------------------------|-------------------------------------|
| KUBE_VERSION  | Kubernetes release to package               | Latest stable version       |
| ETCD_VERSION  | Version of etcd                                              | 3.3.4                                       |
| CNI_VERSION      | Version of CNI tools                                    | 0.7.1                                       |
| KUBE_TRACK       | Kubernetes series (e.g., 1.10) to package | Latest stable                 |
| ISTIO_VERSION   | istio release                                                  | v1.0.0                                     |

For example:

```bash
KUBE_VERSION=v1.9.6 snapcraft
```

## Faster builds

To speed-up the build process you can reuse the binaries already downloaded from a
previous build. Binaries are placed under `parts/microk8s/build/build/kube_bins`.
All you need to do is to make a copy of this directory and have the `KUBE_SNAP_BINS`
environment variable point to it.

After a standard build, run the following:

```bash
cp -r parts/microk8s/build/build/kube_bins .
export KUBE_SNAP_BINS=$PWD/kube_bins/v1.12.2/
snapcraft
 ```

...this build will be much faster and will reuse binaries in `KUBE_SNAP_BINS`
