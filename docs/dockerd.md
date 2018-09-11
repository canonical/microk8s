# Dockerd in microk8s

The docker daemon used by microk8s is listening on `unix:///var/snap/microk8s/docker.sock`. You can access it with the `microk8s.docker` command. To skip the `microk8s` prefix we suggest you employ a snap alias:
```
sudo snap alias microk8s.docker docker
docker ps
```

When AppArmor is enabled all docker daemons running in a system will apply the same `docker-default` profile on running containers. Each daemon makes sure that it is the only process manging the docker containers (eg send start stop signals). Effectively this allowes only one dockerd running on any host. Therefore, you have to make sure no other dockerd is running on your sytem along with microk8s.

Restarting microk8s' dockerd (`sudo systemctl restart snap.microk8s.daemon-docker`) or calling the `microk8s.reset` command will ensure the correct AppArmor profile is loaded.

## References
 - Issue describing the AppArmor profile limitation: https://forum.snapcraft.io/t/commands-and-aliases/3950
