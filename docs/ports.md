# Services Exposed and Ports Used

For now microk8s is meant to be used for local development thus certain security issues are not addressed at this point. Here we present the ports and sockets each service uses as well as the default authorisation and authentication configuration.

Services can be placed in two groups based on the network interface they are bind to. Services binding to the localhost interface are only available from within the host and we take no action to protect them. Services binding to the default host interface are available from outside the host and thus we enforce some form of access restrictions. The ports used by both types of services need to be free so that microk8s starts successfully.

### Services Binging to the Default Host Interface

Port | Service | Access Restrictions
--- | --- | ---
6443 | API server | SSL encrypted. Clients need to present a valid password from a [Static Password File](https://kubernetes.io/docs/reference/access-authn-authz/authentication/#authentication-strategies).
10250 | kubelet | Anonymous authentication is disabled. [X509 client certificate](https://kubernetes.io/docs/reference/command-line-tools-reference/kubelet-authentication-authorization/) is required.
10255 | kubelet | Read only port for the Kubelet.
random | kube-proxy | One random port per hosted service is opened as we use `--proxy-mode=userspace` for compatibility reasons.

If you remove `--proxy-mode` from `/var/snap/microk8s/current/args/kube-proxy` and `sudo systemctl restart snap.microk8s.daemon-proxy` kube-proxy will stop exposing the cluster hosted services.


### Services Binging to the localhost Interface

Port | Service | Description
--- | --- | ---
8080 | API server | Port for insecure communication to the API server
10248 | kubelet | Localhost healthz endpoint.
10249 | kube-proxy | Port for the metrics server to serve on.
10251 | kube-schedule | Port on which to serve HTTP insecurely.
10252 | kube-controller | Port on which to serve HTTP insecurely.
10256 | kube-proxy | Port to bind the health check server.

Note that this is not an exhaustive list of ports used.

### Docker and etcd

Both these services are exposed through unix sockets.

Service | Socket
--- | ---
docker | unix:///var/snap/microk8s/current/docker.sock
etcd | unix://etcd.socket:2379


## Authentication and Authorization

Upon a new deployment microk8s creates a new CA, a signed server certificate and a service account key file. These files are stored under `/var/microk8s/current/certs`. Kubelet an the API server are aware of the same CA and so the signed server certificate is used by the API server to authenticate with kubelet (`--kubelet-client-certificate`). Clients talking to the secure port of the API server (`6443`) have to also be aware of the CA (`certificate-authority-data` in user kubeconfig).

Authentication of users is done with a [Static Password File](https://kubernetes.io/docs/reference/access-authn-authz/authentication/#authentication-strategies) also generated at first microk8s deployment. Password tokens and usernames are stored in the `basic_token.csv` file available under `/var/snap/microk8s/current/credentials/`. Also under `/var/snap/microk8s/current/credentials/` you can find the `client.config` kubeconfig file used by `microk8s.kubectl`.

Currently all requests coming from authenticated sources are authorized as we have configured the api-server with `--authorization-mode=AlwaysAllow`.


## References

 - Authentication strategies: https://kubernetes.io/docs/reference/access-authn-authz/authentication/#authentication-strategies
 - kubelet: https://kubernetes.io/docs/reference/command-line-tools-reference/kubelet/
 - kube-proxy: https://kubernetes.io/docs/reference/command-line-tools-reference/kube-proxy/
 - kube-scheduler: https://kubernetes.io/docs/reference/command-line-tools-reference/kube-scheduler/
 - kube-controller-manager: https://kubernetes.io/docs/reference/command-line-tools-reference/kube-controller-manager/

