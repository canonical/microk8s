# Private Registry Addon

Having a private docker registry can significantly improve your productivity by reducing the time spent in uploading and downloading docker images. The registry shipped with microk8s is hosted within the kubernetes cluster and is exposed as a NodePort service on port `32000` of the `localhost`. Note that this is an insecure registry and you may need to take extra steps to limit access to it.


## Installation and Usage

You can install the registry with:
```
microk8s.enable registry
```

As you can see in the applied [manifest](../microk8s-resources/actions/registry.yaml) a `20Gi` persistent volume is claimed for storing images. To satisfy this claim the storage addon is also enabled along with the registry.

The docker daemon used by microk8s is [configured to trust](../microk8s-resources/default-args/docker-daemon.json) this insecure registry. It is on this daemon we will have to talk to when we want to upload images. The easiest way to do so is by using the `microk8s.docker` client:

```
microk8s.docker pull busybox
microk8s.docker tag busybox localhost:32000/my-busybox
microk8s.docker push localhost:32000/my-busybox
```

If you prefer to use an external docker client you should point it to the socket dockerd is listening on:
```
docker -H unix:///var/snap/microk8s/docker.sock ps
```

To consume an image from the local registry we need to reference it in our yaml manifests:
```
apiVersion: v1
kind: Pod
metadata:
  name: busybox
  namespace: default
spec:
  containers:
  - name: busybox
    image: localhost:32000/my-busybox
    command:
      - sleep
      - "3600"
    imagePullPolicy: IfNotPresent
  restartPolicy: Always
```


## References
 - Insecure registry: https://docs.docker.com/registry/insecure/
 - Test a registry: https://docs.docker.com/registry/deploying/#copy-an-image-from-docker-hub-to-your-registry
