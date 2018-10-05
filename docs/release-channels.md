# Release Channels and Upgrades

Microk8s is a snap deploying Kubernetes. Upstream Kubernetes ships a new release about every three months, while old releases get periodic updates. At the time of this writing the latest release series is `v1.12` with `v1.12.0` being the latest release. On the `v1.11` series, `v1.11.3` is the latest release. It is important to remember that upstream Kubernetes is committed to maintain backwards compatibility only within a release series. That means that your Kubernetes will not break due to API changes when you upgrade from `v1.11.x` to `v1.11.y` but may break if you upgrade from `v1.11.x` to `v1.12.z`.


## Choosing the Right Channel

When installing microk8s you can select your desired upstream Kubernetes series with the corresponding snap channel. For example, to install microk8s and let it follow the `v1.12` release series you:

```
snap install microk8s --classic --channel=1.12/stable
```

If you omit the `--channel` argument microk8s will follow the latest stable upstream Kubernetes. This means that your deployment will eventually upgrade to a new release series. At the time of this writing you will get `v1.12.0` with:

```
snap install microk8s --classic
```

Since no `--channel` is specified such deployment will eventually upgrade to `v1.13.0`.


Switching from one channel to another is done with [`snap refresh --channel=<new_channel>`](https://docs.snapcraft.io/reference/snap-command#refresh). For example, switch microk8s to the v1.11 release series with:

```
snap install microk8s --channel=1.11/stable
```

## Availability of Releases and Channels

The `*/stable` channels serve the latest stable upstream Kubernetes release of the respective release series. Upstream releases are propagated to the microk8s snap in about a week. This means your microk8s will upgrade to the latest upstream release in your selected channel roughly one week after the upstream release.

The `*/candidate` and `*/beta` channels get updated within hours of an upstream release. Getting a microk8s deployment pointing to `1.12/beta` is as simple as:

```
snap install microk8s --classic --channel=1.12/beta
```

The `*/edge` channels get updated for each microk8s patch or upstream Kubernetes release.

Keep in mind that edge and beta are snap constructs and do not relate to Kubernetes release names.

## Summary

To always track the latest stable Kubernetes versions:

```
snap install microk8s --classic
```

To track the latest version in a specific release series:

```
snap install microk8s --classic --channel=<track>/stable
```
