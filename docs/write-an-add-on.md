# How to write an add-on

Add-ons are a convenient way for the end user to `microk8s.enable` a certain functionality.

Add-ons are shipped with MicroK8s so we have to
[build the MicroK8s snap](docs/build-the-snap-from-source.md)
to test the add-on we are introducing.


## Simple yaml manifests

The simplest add-on is a yaml manifest placed in the actions
directory https://github.com/ubuntu/microk8s/tree/master/microk8s-resources/actions.
The name of the add-on is the name of the yaml filename.

As soon as the user `microk8s.enable foo` the
[enable action wrapper](https://github.com/ubuntu/microk8s/blob/master/microk8s-resources/wrappers/microk8s-enable.wrapper#L46)
searches for a `foo.yaml` and kubectl applies it.

Remember, we need to build and deploy the snap so as the yaml manifest
is in the designated location.

At the time of this writing an example of this kind of add-on is the `metrics-server.yaml`.
As the metrics server deployment is made of multiple yaml manifests we had to consolidate all of them
in a single yaml.


## Add-ons in enable scripts

The [enable action wrapper](https://github.com/ubuntu/microk8s/blob/master/microk8s-resources/wrappers/microk8s-enable.wrapper#L35)
will run shell scripts in addition to applying yaml manifests.
This means that if we put a script called `enable.foo.sh` in the actions
directory https://github.com/ubuntu/microk8s/tree/master/microk8s-resources/actions
we will get a `microk8s.enable foo` action. The add-on script approach is very powerful as
it can do things like apply manifests, reconfigure servers, download binaries etc.

Similarly you could have a `disable.foo.sh` script to handle the `microk8s.disable foo` case.


### Add-ons with large binaries

We try to keep the MicroK8s binary small so as the installation time is short.
Often add-on are used to enhance the set of `microk8s` commands on demand.
This will get clear     


## Further reading
- [build the MicroK8s snap](docs/build-the-snap-from-source.md)
