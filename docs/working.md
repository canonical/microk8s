# Working with image registries

Kubernetes manages containerised applications based on images. These images can
be created locally, or more commonly are fetched from a remote image registry.
The following documentation explains how to use MicroK8s with local images, or
images fetched from public or private registries.

A familiarity with building, pushing and tagging container images will be
helpful. These examples use Docker but you can use your preferred
container tool chain.

To install Docker on Ubuntu 18.04:

```
sudo apt-get install docker.io
```

Add the user to the `docker` group:

```bash
sudo usermod -aG docker ${USER}
```

Open a new shell for the user, with updated group membership:

```bash
su - ${USER}
```

The Dockerfile we will be using is:

```
FROM nginx:alpine
```

To build the image tagged with `mynginx:local`, navigate to the directory where
`Dockerfile` is and run:

```bash
docker build . -t mynginx:local
```

This will generate a new local image tagged `mynginx:local`.

## Working with locally built images without a registry

When an image is built it is cached on the Docker daemon used during the build.
Having run the `docker build . -t mynginx:local` command, you can see the newly built image by
running:

```bash
docker images
```

This will list the images currently known to Docker, for example:

```no-highlight
REPOSITORY          TAG                 IMAGE ID            CREATED             SIZE
mynginx             local               1fe3d8f47868        30 minutes ago      16.1MB
```

The image we created is known to Docker. However, Kubernetes is not aware of
the newly built image. This is because your local  Docker daemon is not part of
the MicroK8s Kubernetes cluster. We can export the built image from the local
Docker daemon and "inject" it into the  MicroK8s image cache like this:

```bash
docker save mynginx > myimage.tar
microk8s.ctr -n k8s.io image import myimage.tar
```

Note that when we import the image to MicroK8s we do so under the `k8s.io` namespace
(the `-n k8s.io` argument).

Now we can list the images present in MicroK8s:

```bash
microk8s.ctr -n k8s.io images ls
```

At this point we are ready to `microk8s.kubectl apply -f` a deployment with this image:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: mynginx:local
        ports:
        - containerPort: 80
```

We reference the image with `image: mynginx:local`. Kubernetes will behave as though
there is an image in docker.io (the Dockerhub registry) for which it already has a cached
copy. This process can be repeated any time changes are made to the image. Note that
containerd will not cache images with the `latest` tag so make sure you avoid it.


## Working with public registries

After building an image with `docker build . -t mynginx:local`, it can be pushed to one of
the mainstream public registries. You will need to create an account and register a
username. For this example we created an account with [https://hub.docker.com/]()  and
we log in as `kjackal`.

First we run the login command:

```bash
docker login
```

Docker will ask for a Docker ID and password to complete the login.

``` no-highlight
Login with your Docker ID to push and pull images from Docker Hub. If you don't have a Docker ID, head over to https://hub.docker.com to create one.
Username: kjackal
Password: *******
```

Pushing to the registry requires that the image is tagged with
`your-hub-username/image-name:tag`. We can either add proper tagging during build:

```bash
docker build . -t kjackal/mynginx:public
```

Or tag an already existing image using the image ID. Obtain the ID by running:

```bash
docker images
```

The ID is listed in the output:

```no-highlight
REPOSITORY          TAG                 IMAGE ID            CREATED             SIZE
mynginx             local              1fe3d8f47868        2 hours ago         16.1MB
....
```

Then use the `tag` command:

```bash
docker tag 1fe3d8f47868 kjackal/mynginx:public
```

Now that the image is tagged correctly, it can be pushed to the registry:

```bash
docker push kjackal/mynginx
```

At this point we are ready to `microk8s.kubectl apply -f` a deployment with our image:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: kjackal/mynginx:public
        ports:
        - containerPort: 80
```

We refer to the image as `image: kjackal/mynginx:public`. Kubernetes will search for the
image in its default registry, `docker.io`.


## Working with MicroK8s' registry add-on

Having a private Docker registry can significantly improve your productivity by reducing
the time spent in uploading and downloading Docker images. The registry shipped with
MicroK8s is hosted within the Kubernetes cluster and is exposed as a NodePort service
on port `32000` of the `localhost`. Note that this is an insecure registry and you may
need to take extra steps to limit access to it.

You can install the registry with:

```bash
microk8s.enable registry
```

The add-on registry is backed up by a `20Gi` persistent volume is claimed for storing
images. To satisfy this claim the storage add-on is also enabled along with the registry.

The containerd daemon used by MicroK8s is configured to trust this insecure registry. To
upload images we have to tag them with `localhost:32000/your-image` before pushing
them:

We can either add proper tagging during build:

```bash
docker build . -t localhost:32000/mynginx:registry
```

Or tag an already existing image using the image ID. Obtain the ID by running:

```bash
docker images
```

The ID is listed in the output:

```no-highlight
REPOSITORY          TAG                 IMAGE ID            CREATED             SIZE
mynginx             local              1fe3d8f47868        2 hours ago         16.1MB
....
```

Then use the `tag` command:

```bash
docker tag 1fe3d8f47868 localhost:32000/mynginx:registry
```

Now that the image is tagged correctly, it can be pushed to the registry:

```bash
docker push localhost:32000/mynginx
```

Pushing to this insecure registry may fail in some versions of Docker unless the daemon
is explicitly configured to trust this registry. To address this we need to edit
`/etc/docker/daemon.json` and add:

```json
{
  "insecure-registries" : ["localhost:32000"]
}
```

The new configuration should be loaded with a Docker daemon restart:

```bash
sudo systemctl restart docker
```

At this point we are ready to `microk8s.kubectl apply -f` a deployment with our image:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: localhost:32000/mynginx:registry
        ports:
        - containerPort: 80
```

### What if MicroK8s runs inside a VM?

Often MicroK8s is placed in a VM while the development process takes place on the host
machine. In this setup pushing container images to the in-VM registry requires some
extra configuration.

Let's assume the IP of the VM running MicroK8s is `10.141.241.175`. When we are on the
host the Docker registry is not on `localhost:32000` but on `10.141.241.175:32000`. As a
result the first thing we need to do is to tag the image we are building on the host with
the right registry endpoint:

```bash
docker build . -t 10.141.241.175:32000/mynginx:registry
```

If we immediately try to push the `mynginx` image we will fail because the local Docker
does not trust the in-VM registry. Here is what happens if we try a push:

```bash
docker push  10.141.241.175:32000/mynginx
```
```no-highlight
The push refers to repository [10.141.241.175:32000/mynginx]
Get https://10.141.241.175:32000/v2/: http: server gave HTTP response to HTTPS client
```

We need to be explicit and configure the Docker daemon running on the host to trust the
in-VM insecure registry. Add the registry endpoint in `/etc/docker/daemon.json`:

```json
{
  "insecure-registries" : ["10.141.241.175:32000"]
}
```

Then restart the docker daemon on the host to load the new configuration:

```bash
sudo systemctl restart docker
```

We can now `docker push  10.141.241.175:32000/mynginx` and see the image getting
uploaded. During the push our Docker client instructs the in-host Docker daemon to
upload the newly built image to the `10.141.241.175:32000` endpoint as marked by the
tag on the image. The Docker daemon sees (on `/etc/docker/daemon.json`) that it trusts
the registry and proceeds with uploading the image.

Consuming the image from inside the VM involves no changes:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: localhost:32000/mynginx:registry
        ports:
        - containerPort: 80
```

Reference the image with `localhost:32000/mynginx:registry` since the registry runs
inside the VM so it is on `localhost:32000`.


## Working with a private registry

Often organisations have their own private registry to assist collaboration and accelerate
development. Kubernetes (and thus MicroK8s) need to be aware of the registry
endpoints before being able to pull container images.

### Insecure registry

Let's assume the private insecure registry is at `10.141.241.175` on port `32000`. The
images we build need to be tagged with the registry endpoint:

```bash
docker build . -t 10.141.241.175:32000/mynginx:registry
```

Pushing  the `mynginx` image at this point will fail because the local Docker does not
rust the private insecure registry. The docker daemon used for building images should be
configured to trust the private insecure registry. This is done by marking the registry
endpoint in `/etc/docker/daemon.json`:

```json
{
  "insecure-registries" : ["10.141.241.175:32000"]
}
```

Restart the Docker daemon on the host to load the new configuration:

```
sudo systemctl restart docker
```

Now  running
```bash
docker push  10.141.241.175:32000/mynginx
```
...should succeed in uploading the image to the registry.

Attempting to pull an image in MicroK8s at this point will result in an error like this:

```no-highlight
  Warning  Failed             1s (x2 over 16s)  kubelet, jackal-vgn-fz11m  Failed to pull image "10.141.241.175:32000/mynginx:registry": rpc error: code = Unknown desc = failed to resolve image "10.141.241.175:32000/mynginx:registry": no available registry endpoint: failed to do request: Head https://10.141.241.175:32000/v2/mynginx/manifests/registry: http: server gave HTTP response to HTTPS client
```

We need to edit `/var/snap/microk8s/current/args/containerd-template.toml` and add
the following under `[plugins] -> [plugins.cri.registry] -> [plugins.cri.registry.mirrors]`:

```
        [plugins.cri.registry.mirrors."10.141.241.175:32000"]
          endpoint = ["http://10.141.241.175:32000"]
```

See the full file [here](/docs/containerd-template.toml).

Restart MicroK8s to have the new configuration loaded:

```bash
microk8s.stop
```

Allow a few seconds for the service to close fully before starting again:

```bash
microk8s.start
```

The image can now be deployed with:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: 10.141.241.175:32000/mynginx:registry
        ports:
        - containerPort: 80
```

Note that the image is referenced with `10.141.241.175:32000/mynginx:registry`.

### Secure registry

There are a lot of ways to setup a private secure registry that may slightly change the
way you interact with it. Instead of diving into the specifics of each setup we provide
here two pointers on how you can approach the integration with Kubernetes.

-   In the [official Kubernetes documentation][kubernetes-docs] a method is described for
  creating a secret from the Docker login credentials and using this to access the secure
  registry. To achieve this, `imagePullSecrets` is used as part of the container spec.

-   MicroK8s v1.14 and onwards uses **containerd**. [As described here](https://github.com/containerd/cri/blob/master/docs/registry.md)
  to be aware of the secure registry and the credentials needed to access it.
  As shown above, configuring containerd involves editing
  `/var/snap/microk8s/current/args/containerd-template.toml` and reloading the
  new configuration via a `microk8s.stop`, `microk8s.start` cycle.


# Further Reading

-   [Test an insecure registry](https://docs.docker.com/registry/insecure/)
-   [Configuring containerd](https://github.com/containerd/cri/blob/master/docs/registry.md)
-   [Upstream Kubernetes documentation on pulling images from a private registry][kubernetes-docs]


[containerd-template]: /containerd-template.toml
[kubernetes-docs]: https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/
