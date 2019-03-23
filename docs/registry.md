# Private Registry Addon

Having a private docker registry can significantly improve your productivity by reducing the time spent in uploading and downloading docker images. The registry shipped with MicroK8s is hosted within the kubernetes cluster and is exposed as a NodePort service on port `32000` of the `localhost`. Note that this is an insecure registry and you may need to take extra steps to limit access to it.


## Installation and Usage

You can install the registry with:
```
microk8s.enable registry
```

As you can see in the applied [manifest](../microk8s-resources/actions/registry.yaml) a `20Gi` persistent volume is claimed for storing images. To satisfy this claim the storage addon is also enabled along with the registry.

The containerd daemon used by MicroK8s is [configured to trust](../microk8s-resources/default-args/containerd-template.toml) this insecure registry. The easiest way to upload images to the registry is using the docker client:

```
docker pull busybox
docker tag busybox localhost:32000/my-busybox
docker push localhost:32000/my-busybox
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
 - Containerd registry: https://github.com/containerd/cri/blob/master/docs/registry.md
