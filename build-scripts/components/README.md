# Parts directory

This directory contains the build scripts for Go components built into MicroK8s.

The directory structure looks like this:

```
build-scripts/
    build-component.sh              <-- runs as `build-component.sh $component_name`
                                        - checks out the git repository
                                        - runs the `pre-patch.sh` script (if any)
                                        - applies the patches (if any)
                                        - runs the `build.sh` script to build the component
    component/
        $component_name/
            repository              <-- git repository to clone
            version.sh              <-- prints the repository tag or commit to checkout
            build.sh                <-- runs as `build.sh $output $version`
                                        first argument is the output directory where
                                        binaries should be placed, second is the component version
            pre-patch.sh            <-- runs as `pre-patch.sh`. takes any action needed before applying
                                        the component patches
            patches/                <-- list of patches to apply after checkout (see section below)
                ...
            strict-patches/         <-- list of extra patches to apply when building strictly confined snap
                ...
```

## Applying patches

Most MicroK8s components are retrieved from an upstream source (specified in the `repository`), with a specific tag (specified in `version.sh`), have some patches applied to them (from the `patches/` and `strict-patches/` directories) and are then built (using `build.sh`).


This section explains the directory format for the `patches` and `strict-patches` directories. The same rules apply for both. Note that the `strict-patches` (if any) are applied **after** any `patches` have been applied.

Our patches do not frequently change between versions, but they do have to be rebased from time to time, which breaks compatibility with older versions. For that reason, we maintain a set of patches for each version that introduces a breaking change. Consider the following directory structure for the Kubernetes component.

```
patches/default/0.patch
patches/v1.27.0/a.patch
patches/v1.27.0/b.patch
patches/v1.27.4/c.patch
patches/v1.28.0/d.patch
patches/v1.28.0-beta.0/e.patch
```

The Kubernetes version to build may be decided dynamically while building the snap, or be pinned to a specified version. The following table shows which patches we would apply depending on the Kubernetes version that we build:

| Kubernetes version | Applied patches         | Explanation                                                                                |
| ------------------ | ----------------------- | ------------------------------------------------------------------------------------------ |
| `v1.27.0`          | `a.patch` and `b.patch` |                                                                                            |
| `v1.27.1`          | `a.patch` and `b.patch` | In case there is no exact match, find the most recent older version                        |
| `v1.27.4`          | `c.patch`               | Older patches are not applied                                                              |
| `v1.27.12`         | `c.patch`               | In semver, `v1.27.12 > v1.27.4` so we again must get the most recent patches               |
| `v1.28.0-rc.0`     | `d.patch`               | Extra items from semver are ignored, so we can define the `v1.28.0` patch and be done      |
| `v1.28.0-beta.0`   | `e.patch`               | Extra items from semver are ignored, but due to exact match this patch is used instead     |
| `v1.28.0`          | `d.patch`               | Extra items from semver are ignored, so we can define the `v1.28.0` patch and be done      |
| `v1.28.4`          | `d.patch`               | Picks the patches from the stable versions only, not from beta                             |
| `v1.29.1`          | `d.patch`               | Uses patches from most recent version, even if on a different minor                        |
| `hack/branch`      | `0.patch`               | If not semver and no match, any patches from the `default/` directory are applied (if any) |

Same logic applies for all other components as well.

### Testing which patches would be applied

You can verify which set of patches would be applied in any case using the `print-patches-for.py` script directly:

```bash
$ ./build-scripts/print-patches-for.py kubernetes v1.27.4
/home/ubuntu/microk8s/build-scripts/components/kubernetes/patches/v1.27.4/0000-Kubelite-integration.patch
$ ./build-scripts/print-patches-for.py kubernetes v1.27.3
/home/ubuntu/microk8s/build-scripts/components/kubernetes/patches/v1.27.0/0000-Kubelite-integration.patch
/home/ubuntu/microk8s/build-scripts/components/kubernetes/patches/v1.27.0/0001-Unix-socket-skip-validation-in-component-status.patch
$ ./build-scripts/print-patches-for.py kubernetes v1.28.1
/home/ubuntu/microk8s/build-scripts/components/kubernetes/patches/v1.28.0/0001-Set-log-reapply-handling-to-ignore-unchanged.patch
/home/ubuntu/microk8s/build-scripts/components/kubernetes/patches/v1.28.0/0000-Kubelite-integration.patch
```

### How to add support for newer versions

When a new release comes out which is no longer compatible with the existing latest patches, simply create a new directory under `patches/` with the new version number. This ensures that previous versions will still work, and newer ones will pick up the fixed patches.
