# Image registries: Working with ...

Kubernetes deploys and manages containarised applications. Such applications are packaged into container images stored on container registries. Here we describe the different ways of working with registries and the configuration steps needed for MicroK8s to integrate with each workflow.

In what follows we assume you are are able to build, push, pull and run container images. We use docker but you can use your preferred container tool chain.

To install docker on an Ubuntu 18.04 we:
```
sudo apt-get install docker.io

sudo usermod -aG docker ${USER}
# Get a new shell with the new set of user groups
su - ${USER}
```

The Dockerfile we will be using is:
```
FROM nginx:alpine
```


To build the image we navigate to the directory with the `Dockerfile` and issue:
```
docker build . -t mynginx:latest
```

## ... locally build images and no registry

When an image is freshly build it is cached on the docker daemon used during the build. Following the  `docker build .` you can see the freshly build image with:
```
> docker images
REPOSITORY          TAG                 IMAGE ID            CREATED             SIZE
mynginx             latest              1fe3d8f47868        30 minutes ago      16.1MB
nginx               alpine              0be75340bd9b        6 days ago          16.1MB
```

Kubernetes is not aware of the newly built image as your local docker daemon is not exposing any cached images. We can however export the newly build image from the local docker daemon and "inject" it in to the images MicroK8s has cached. Here is how to do this:
```
docker save mynginx > myimage.tar
microk8s.ctr -n k8s.io image import myimage.tar
```
Note that when we import the image to MicroK8s we do so under the `k8s.io` namespace (`-n k8s.io` argument)

To see the images present in MicroK8s:
```
microk8s.ctr -n k8s.io images ls
```

At this point we are ready to `microk8s.kubectl apply -f` a deployment with this image:
```
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
        image: mynginx:latest
        ports:
        - containerPort: 80
```

We use reference the image with `image: mynginx:latest`. Kubernetes believes there is an image in docker-hub for which the image is already cached.


## ... public registry

Right after building our image with `docker build . -t mynginx:latest` we can push it to one of the mainstream public registries. You will need to create an account at so as to register a username. Here after creating an account at https://hub.docker.com/  we login as `kjackal`.

```
> docker login
Login with your Docker ID to push and pull images from Docker Hub. If you don't have a Docker ID, head over to https://hub.docker.com to create one.
Username: kjackal
Password: *******
```


Pushing to the registry requires that we have tagged our image with `your-hub-username/image-name:tag`. We can either add proper tagging during build:
```
docker build . -t kjackal/mynginx:public
```

Or tag an already existing image with:
```
> docker images
REPOSITORY          TAG                 IMAGE ID            CREATED             SIZE
mynginx             latest              1fe3d8f47868        2 hours ago         16.1MB
....
> docker tag 1fe3d8f47868 kjackal/mynginx:public
```

Pushing the image to the public repository is what we need to do next:
```
docker push kjackal/mynginx
```

At this point we are ready to `microk8s.kubectl apply -f` a deployment with our image:
```
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

We use reference the image with `image: kjackal/mynginx:public`. Kubernetes will search for the image in its default registry `docker.io`.


## ... MicroK8s' local registry

Having a private docker registry can significantly improve your productivity by reducing the time spent in uploading and downloading docker images. The registry shipped with MicroK8s is hosted within the Kubernetes cluster and is exposed as a NodePort service on port `32000` of the `localhost`. Note that this is an insecure registry and you may need to take extra steps to limit access to it.

You can install the registry with:
```
microk8s.enable registry
```

As you can see in the applied [manifest](../microk8s-resources/actions/registry.yaml) a `20Gi` persistent volume is claimed for storing images. To satisfy this claim the storage add-on is also enabled along with the registry.

The containerd daemon used by MicroK8s is [configured to trust](../microk8s-resources/default-args/containerd-template.toml) this insecure registry. To upload images to the registry you have to tag them with `localhost:32000/your-image` before pushing them:

We can either add proper tagging during build:
```
docker build . -t localhost:32000/mynginx:registry
```

Or tag an already existing image with:
```
> docker images
REPOSITORY          TAG                 IMAGE ID            CREATED             SIZE
mynginx             latest              1fe3d8f47868        2 hours ago         16.1MB
....
> docker tag 1fe3d8f47868 localhost/mynginx:registry
```

Pushing the image to the registry repository is what we need to do next:
```
docker push localhost:32000/mynginx
```

Pushing to our insecure registry may fail in some versions of docker unless the daemon is explicitly configured to trust our registry. To do so we need to add in `/etc/docker/daemon.json`:
```
{
  "insecure-registries" : ["localhost:32000"]
}
```

And restart the docker daemon with:
```
sudo systemctl restart docker
```


To consume an image from the local registry we need to reference it in our yaml manifests:
```
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

### what if MicroK8s runs inside a VM?

Often MicroK8s is placed in a VM while the development process takes place on the host machine. Is this setup pushing container images to the in-VM registry requires some extra configuration.

Let's assume the IP of the VM running MicroK8s is `10.141.241.175`. When on host the docker registry is not on `localhost:32000` but on `10.141.241.175:32000`. As a result the first thing we need to do is to tag the image we are building on the host with the right registry endpoint:
```
docker build . -t 10.141.241.175:32000/mynginx:registry
```

If we immediately try to push the `mynginx` image we will fail because the local docker does not trust the in-VM registry. Here is what happens if we do:
```
> docker push  10.141.241.175:32000/mynginx
The push refers to repository [10.141.241.175:32000/mynginx]
Get https://10.141.241.175:32000/v2/: http: server gave HTTP response to HTTPS client

```

We need to be explicit and configure the docker daemon running on the host to trust the in-VM insecure registry. To do so we add the registry endpoint in `/etc/docker/daemon.json`:
```
{
  "insecure-registries" : ["10.141.241.175:32000"]
}
```

And restart the docker daemon on the host with:
```
sudo systemctl restart docker
```

We can now `docker push  10.141.241.175:32000/mynginx` again and see the image getting uploaded. During the push our docker client instructs the in-host docker daemon to upload the newly build image to the `10.141.241.175:32000` endpoint as marked by the tag on the image. The docker daemon sees (on `/etc/docker/daemon.json`) that is trusts the registry and proceeds with uploading the image.

Consuming the image from inside the VM involves no changes:
```
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

We reference the image with `localhost:32000/mynginx:registry` since the registry runs inside the VM so it is on `localhost:32000`.


## ... private registry

Often organisations have their own private registry to assist collaboration and accelerate development. Kubernetes (and MicroK8s of course) need to be aware of the registry endpoints before being able to pull container images.

### insecure registry

As we did above let's assume the private insecure is at `10.141.241.175` on port `32000`. The images we build need to be tagged  with the registry endpoint:
```
docker build . -t 10.141.241.175:32000/mynginx:registry
```

Pushing immediately the `mynginx` image we will fail because the local docker does not trust the private insecure registry so we need to configure the docker daemon we use for building images to trust the private insecure registry. This is done by marking the registry endpoint in `/etc/docker/daemon.json`:
```
{
  "insecure-registries" : ["10.141.241.175:32000"]
}
```

And restarting the docker daemon with:
```
sudo systemctl restart docker
```

Now `docker push  10.141.241.175:32000/mynginx` uploads the image to the registry.

If we try to pull an image in MicroK8s at this point we will get an error like this one:
```
  Warning  Failed             1s (x2 over 16s)  kubelet, jackal-vgn-fz11m  Failed to pull image "10.141.241.175:32000/mynginx:registry": rpc error: code = Unknown desc = failed to resolve image "10.141.241.175:32000/mynginx:registry": no available registry endpoint: failed to do request: Head https://10.141.241.175:32000/v2/mynginx/manifests/registry: http: server gave HTTP response to HTTPS client
```

We need to edit `/var/snap/microk8s/current/args/containerd-template.toml` and add the following under `[plugins] -> [plugins.cri.registry] -> [plugins.cri.registry.mirrors]`:
```
        [plugins.cri.registry.mirrors."10.141.241.175:32000"]
          endpoint = ["http://10.141.241.175:32000"]
```
See the full file [here](containerd-template.toml)

Restart MicroK8s to have the new configuration loaded:
```
microk8s.stop
# give it a few seconds
microk8s.start
```

Consuming the image from our private insecure registry is done with:
```
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

We reference the image with `10.141.241.175:32000/mynginx:registry`.

### secure registry

There are a lot of ways to setup a private secure registry that may slightly change the way you interact with it. Instead of diving into the specific of each and every setup we provide here a few pointers to how you can approach the integration with MicroK8s.

- In the [official Kubernetes documentation](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/) you are presented with a way to create a secret from the docker login credentials and attach have the secret used whenever you want to pull an image from the secure registry. To achieve this `imagePullSecrets` is used as part of the container spec.

- MicroK8s v1.14 and onwards is using containerd. Containerd [can be configured](https://github.com/containerd/cri/blob/master/docs/registry.md) to be aware of the secure registry and the credentials needed to access it. As we shown above configuring containerd involves editing `/var/snap/microk8s/current/args/containerd-template.toml` and reloading the new configuration via a `microk8s.stop`, `microk8s.start` cycle.



# References

- [Test an insecure registry](https://docs.docker.com/registry/insecure/)
- [Configuring containerd](https://github.com/containerd/cri/blob/master/docs/registry.md)
- [Upstream Kubernetes documentation on pulling images from a private registry](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/)