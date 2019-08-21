# How to add a user

The upstream [authentication docs](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
describe a few methods for adding users. MicroK8s is by default configured to authenticate users via
a [static tokens file](https://kubernetes.io/docs/reference/access-authn-authz/authentication/#static-token-file),
  [x509 client certs](https://kubernetes.io/docs/reference/access-authn-authz/authentication/#x509-client-certs), and
a [static password file](https://kubernetes.io/docs/reference/access-authn-authz/authentication/#static-password-file).
Here we show how to add a user using the static password file method.

### Configuring Kubernetes

Edit the passwords file at `/var/snap/microk8s/current/credential/basic_auth.csv` and add an entry of the form:
```
token,user,uid,"group1,group2,group3"
```

- the token should be a random string
- the user is just a username
- the uid is something that uniquely identifies the user "and attempts to be more consistent and unique than username"
- the groups the user belongs to. Groups make sense in the context of [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).

Here is an example entry where the superk8s user belongs to the "system:masters" group:
```
TC9zQ1VkWitqYWpRV2tKQkkzd3FKT2p6QmJydEtaxxxRMEl3VjQ4ekpaaz0K,superk8s,superk8s,"system:masters"
```

You need to restart the services for the new user to be loaded.
```
sudo microk8s.stop
sudo microk8s.start
```


### Generating a kubeconfig file for the new user
Let's use the default kubeconfig file as a template:
```
sudo microk8s.config > ~/config
```

Edit the `~/config` file and replace all references to admin with the new username and the token used in the password
field with whatever token the new user has. For the example above the config file should look similar to this:
```
apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLSZjTpNVEkzT$
    server: https://172.31.20.243:16443
  name: microk8s-cluster
contexts:
- context:
    cluster: microk8s-cluster
    user: superk8s
  name: microk8s
current-context: microk8s
kind: Config
preferences: {}
users:
- name: superk8s
  user:
    username: superk8s
    password: TC9zQ1VkWitqYWpRV2tKQkkzd3FKT2p6QmJydEtaxxxRMEl3VjQ4ekpaaz0K

```

To access the cluster with the new user we need to provide the newely created kubeconfig file:
```
sudo microk8s.kubectl --kubeconfig ~/config get all --all-namespaces
```

## Further Reading
- https://kubernetes.io/docs/reference/access-authn-authz/authentication/
- https://kubernetes.io/docs/reference/access-authn-authz/rbac/
