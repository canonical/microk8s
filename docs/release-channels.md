# Release Channels and Upgrades

Microk8s is a snap deploying Kubernetes. Upstream Kubernetes ships a new releases every about three months, while old releases get periodic updates. At the time of this writing the latest release series is `v1.12` with `v1.12.0` being the latest release. On the `v1.13` series, `v1.11.3` is the latest release. It is important to remember that upstream Kubernetes is committed to maintain backwards compatibility only within a release series. That means that your kubernetes will not break while you upgrade from `v1.11.x` to `v1.11.y` but may break if you upgrade from `v1.11.x` to `v1.12.z`.


## Choosing the Right Channel

When installing microk8s you can select a channel that reflects the upstream Kubernetes series. To install microk8s and let if follow the `v1.12` release series you:

```
snap install microk8s --classic --channel=1.12/stable
```

If you omit the `--channel` argument microk8s will follow the latest stable upstream Kubernetes. This means that your deployment will eventually upgrade to a new release series. At the time of this writing you will get `v1.12.0` with:

```
snap install microk8s --classic
```

Since no `--channel` is specified such deployment will eventually upgrade to `v1.13.0`.


Switching from one channel to another is done with [`snap refresh --channel=<new_channel>`](https://docs.snapcraft.io/reference/snap-command#refresh). For example, have microk8s switch to `v1.11` release series with:

```
snap install microk8s --channel=1.11/stable
```

## Availablity of Releases and Channels

The `*/stable` channels serve the latest stable upstream Kubernetes release of the respective release series. The upstream releases reach the microk8s stable channel after a week of being released upstream. To put it simply, your microk8s will upgrade after a week an upstream release is made available.

The `*/candidate` and `*/beta` channels get updated within hours of an upstream release. Getting a microk8s deployment pointing to `1.12/beta` is as simple as:

```
snap install microk8s --classic --channel=1.12/beta
```

The `*/edge` channels get updated on each change microk8s patch or a Kubernetes upstream release.

## Confused? Keep Only This

To always stay on the latest stable with the risk of breaking your deployment when upstream moves to a new release:

```
snap install microk8s --classic
```

To stay on the latest stable within a release series thus maintaining backwards compatibility:

```
snap install microk8s --classic --channel=<track>/stable
```
