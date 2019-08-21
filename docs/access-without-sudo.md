# How to access MicroK8s (almost) without sudo
Using sudo in every interaction may be annoying here are
some option we have to overcome this sudo requirement.

## Use a sudo shell
Get a sudo shell with:
```
sudo -H -s -E
```

In the shell provided we shouldn't need to type sudo.


## Grant access to a user group
We can grant group access to the default kubeconfig file as well as the
file with the kubectl the arguments. Let's assume we want to grant access
to MicroK8s to the ubuntu group:
```
sudo chown root:ubuntu /var/snap/microk8s/current/credentials/
sudo chown root:ubuntu /var/snap/microk8s/current/credentials/client.config

sudo chown root:ubuntu /var/snap/microk8s/current/args/
sudo chown root:ubuntu /var/snap/microk8s/current/args/kubectl
```


## Grant access to all local users
We can grant local user access to the default kubeconfig file
and the file with the kubectl arguments:
```
sudo chmod 777 /var/snap/microk8s/current/credentials/
sudo chmod 666 /var/snap/microk8s/current/credentials/client.config

sudo chmod 777 /var/snap/microk8s/current/args/
sudo chmod 666 /var/snap/microk8s/current/args/kubectl
```


## Provide our own kubeconfig file
If we point `microk8s.kubectl` to a kubeconfig file it will not use the
default kubeconfig and will not require elevated permissions.
Let's grab the default kubeconfig file:
```
sudo microk8s.config > ~/.kube/config
```

Have a look at the respective guide on [how to add a user](docs/add-a-user.md)
instead of using the admin credentials.

At this point `microk8s.kubectl --kubeconfig ~/.kube/config` will
not ask for sudo permissions. It will complain about not having access
to the file storing the default kubectl arguments. See one of the methods
above to address this. Alternatively you can use an external `kubectl` after installing it with:
```
sudo snap install kubectl --classic
# pointing kubectl to the user config --kubeconfig ~/.kube/config
kubectl --kubeconfig ~/.kube/config
```


## Further reading
- [How to add a user](docs/add-a-user.md)
- https://github.com/ubuntu/microk8s/issues/606