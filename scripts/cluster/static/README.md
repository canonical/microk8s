# SWAGGER UI

## Overview

swagger.json holds all the schema and used from Swagger UI to generate the relative pages

It is exposed under the url:

https://127.0.0.1:25000/static/swagger.json

## Maintain swagger schema

Under static folder you can find swagger.yaml 

You can copy paste the contents at editor.swagger.io, do any changes, test the ui, and then export to json file so you can update the swagger.json located under static folder

There is also the option to do it vice-versa; update json file, copy the contents at editor.swagger.io, it will convert it to yaml, and copy the contents under /static/swagger.yaml

## Accessing SwaggerUI

The UI can be accessed from this url:
https://127.0.0.1:25000/swagger

## Test calls with curl

### Add the callback-token

```
sudo echo "xyztoken" > /var/snap/microk8s/current/credentials/callback-token.txt
```

### /configure

- Enable dns
```
curl -k -v -d '{"callback":"xyztoken", "addon": [{"name":"dns","enable":true}]}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/configure
```
- Response:
```
{"result": "ok"}
```

### /version
- Get MicroK8s version
```
curl -k -v -d '{"callback":"xyztoken"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/version
```
- Response:
```
v1.17.4
```

You can enable a GET request to get the version without having to provide the token in a json body. To do so, you must create a file with the name 'enable_extended_api' under '/var/snap/microk8s/current/args/enable_extended_api', having the same token value with '/var/snap/microk8s/current/credentials/callback-token.txt'

```
sudo echo "xyztoken" > /var/snap/microk8s/current/args/enable-extended-api
curl -k -v -X GET https://127.0.0.1:25000/cluster/api/v1.0/version
```

### /start
- Start MicroK8s
- Notes: If MicroK8s has been stopped, the cluster-agent will be down to serve any request. 
```
curl -k -v -d '{"callback":"xyztoken"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/start
```
- Response (for already started):
```
Started.
Enabling pod scheduling
node/sx-tpad already uncordoned
```
To start a stopped MicroK8s do it the command way:
```
microk8s.start
```

### /stop
- Stop MicroK8s
```
curl -k -v -d '{"callback":"xyztoken"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/stop
```
- Response:
```
Microk8s will stop but you will probably get a 500 error since the cluster agent will be stopped also
```

### /status
- General status:
```
curl -k -v -d '{"callback":"xyztoken"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/status
```
- Response:
```json
{
    "addons": [{
        "version": 1.6,
        "status": "disabled",
        "name": "cilium",
        "description": "SDN, fast with full network policy"
    }, {
        "version": "2.0.0-beta5",
        "status": "disabled",
        "name": "dashboard",
        "description": "The Kubernetes dashboard"
    }, {
        "version": "1.6.6",
        "status": "disabled",
        "name": "dns",
        "description": "CoreDNS"
    }, {
        "version": null,
        "status": "disabled",
        "name": "fluentd",
        "description": "Elasticsearch-Fluentd-Kibana logging and monitoring"
    }, {
        "version": 1.11,
        "status": "disabled",
        "name": "gpu",
        "description": "Automatic enablement of Nvidia CUDA"
    }, {
        "version": "2.16.0",
        "status": "disabled",
        "name": "helm",
        "description": "Helm 2 - the package manager for Kubernetes"
    }, {
        "version": "3.0.2",
        "status": "disabled",
        "name": "helm3",
        "description": "Helm 3 - Kubernetes package manager"
    }, {
        "version": "0.25.1",
        "status": "disabled",
        "name": "ingress",
        "description": "Ingress controller for external access"
    }, {
        "version": "1.3.4",
        "status": "disabled",
        "name": "istio",
        "description": "Core Istio service mesh services"
    }, {
        "version": "1.14.0",
        "status": "disabled",
        "name": "jaeger",
        "description": "Kubernetes Jaeger operator with its simple config"
    }, {
        "version": "0.9.0",
        "status": "disabled",
        "name": "knative",
        "description": "The Knative framework on Kubernetes."
    }, {
        "version": null,
        "status": "disabled",
        "name": "kubeflow",
        "description": "Kubeflow for easy ML deployments"
    }, {
        "version": "2.7.0",
        "status": "disabled",
        "name": "linkerd",
        "description": "Linkerd is a service mesh for Kubernetes and other frameworks"
    }, {
        "version": "0.8.2",
        "status": "disabled",
        "name": "metallb",
        "description": "Loadbalancer for your Kubernetes cluster"
    }, {
        "version": "0.2.1",
        "status": "disabled",
        "name": "metrics-server",
        "description": "K8s Metrics Server for API access to service metrics"
    }, {
        "version": null,
        "status": "disabled",
        "name": "prometheus",
        "description": "Prometheus operator for monitoring and logging"
    }, {
        "version": null,
        "status": "disabled",
        "name": "rbac",
        "description": "Role-Based Access Control for authorisation"
    }, {
        "version": 2.6,
        "status": "disabled",
        "name": "registry",
        "description": "Private image registry exposed on localhost:32000"
    }, {
        "version": "1.0.0",
        "status": "disabled",
        "name": "storage",
        "description": "Storage class; allocates storage from host directory"
    }],
    "microk8s": {
        "running": true
    }
}
```
- Status for an addon:
```
curl -k -v -d '{"callback":"xyztoken","addon":"dns"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/status
```
- Response:
```json
{"status": "disabled", "addon": "dns"}
```

You can enable a GET request to get the status without having to provide the token in a json body. To do so, you must create a file with the name 'enable_extended_api' under '/var/snap/microk8s/current/args/enable_extended_api', having the same token value with '/var/snap/microk8s/current/credentials/callback-token.txt'

```
sudo echo "xyztoken" > /var/snap/microk8s/current/args/enable-extended-api
curl -k -v -X GET https://127.0.0.1:25000/cluster/api/v1.0/status
```

### /overview
- Get all namespaces
```
curl -k -v -d '{"callback":"xyztoken"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/overview
```

- Response:
```
NAMESPACE     NAME                          READY   STATUS    RESTARTS   AGE
kube-system   pod/coredns-7b67f9f8c-rjq5b   1/1     Running   1          40m

NAMESPACE     NAME                 TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)                  AGE
default       service/kubernetes   ClusterIP   10.152.183.1    <none>        443/TCP                  58m
kube-system   service/kube-dns     ClusterIP   10.152.183.10   <none>        53/UDP,53/TCP,9153/TCP   40m

NAMESPACE     NAME                      READY   UP-TO-DATE   AVAILABLE   AGE
kube-system   deployment.apps/coredns   1/1     1            1           40m

NAMESPACE     NAME                                DESIRED   CURRENT   READY   AGE
kube-system   replicaset.apps/coredns-7b67f9f8c   1         1         1       40m
```

### /config
- Get microk8s config

> YOU MUST enable extended api to make this endpoint ACTIVE. You can enable by creating a file with the name 'enable_extended_api' under '/var/snap/microk8s/current/args/enable_extended_api', having the same token value with '/var/snap/microk8s/current/credentials/callback-token.txt'
```
sudo echo "xyztoken" > /var/snap/microk8s/current/args/enable-extended-api
curl -k -v -d '{"callback":"xyztoken"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/config
```
- Response:
```json
{
    "apiVersion": "v1",
    "clusters": [
        {
            "cluster": {
                "certificate-authority-data": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FUR.......",
                "server": "https://10.22.22.95:16443"
            },
            "name": "microk8s-cluster"
        }
    ],
    "contexts": [
        {
            "context": {
                "cluster": "microk8s-cluster",
                "user": "admin"
            },
            "name": "microk8s"
        }
    ],
    "current-context": "microk8s",
    "kind": "Config",
    "preferences": {},
    "users": [
        {
            "name": "admin",
            "user": {
                "username": "admin",
                "password": "Rkh2TDFrb3htT2NBb1gyVkh6M2pIYXVpblNpRmpwY3loVml6S2l2UjRHTT0K"
            }
        }
    ]
}
```

### /addon/enable
- Enable an addon
```
curl -k -v -d '{"callback":"xyztoken","addon":"dns"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/addon/enable
```
- Response:
```
Enabling DNS
Applying manifest
serviceaccount/coredns created
configmap/coredns created
deployment.apps/coredns created
service/kube-dns created
clusterrole.rbac.authorization.k8s.io/coredns created
clusterrolebinding.rbac.authorization.k8s.io/coredns created
Restarting kubelet
DNS is enabled
```

### /addon/disable
- Disable an addon
```
curl -k -v -d '{"callback":"xyztoken","addon":"dns"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/addon/disable
```

### /services
- Get all available services
```
curl -k -v -d '{"callback":"xyztoken"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/services
```
- Response:
```
{
    "microk8s.daemon-apiserver": "simple, enabled, active",
    "microk8s.daemon-apiserver-kicker": "simple, enabled, active",
    "microk8s.daemon-cluster-agent": "simple, enabled, active",
    "microk8s.daemon-containerd": "simple, enabled, active",
    "microk8s.daemon-controller-manager": "simple, enabled, active",
    "microk8s.daemon-etcd": "simple, enabled, active",
    "microk8s.daemon-flanneld": "simple, enabled, active",
    "microk8s.daemon-kubelet": "simple, enabled, active",
    "microk8s.daemon-proxy": "simple, enabled, active",
    "microk8s.daemon-scheduler": "simple, enabled, active"
}
```

### /service/restart
- Restart a service
```
curl -k -v -d '{"callback":"xyztoken", "service":"microk8s.daemon-flanneld"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/service/restart
```
- Response: 200 OK

### /service/start
- Start a service
```
curl -k -v -d '{"callback":"xyztoken", "service":"microk8s.daemon-flanneld"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/service/start
```
- Response: 200 OK

### /service/stop
- Stop a service
```
curl -k -v -d '{"callback":"xyztoken", "service":"microk8s.daemon-flanneld"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/service/stop
```
- Response: 200 OK

### /service/enable
- Enable a service
```
curl -k -v -d '{"callback":"xyztoken", "service":"microk8s.daemon-flanneld"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/service/enable
```
- Response: 200 OK

### /service/disable
- Disable a service
```
curl -k -v -d '{"callback":"xyztoken", "service":"microk8s.daemon-flanneld"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/service/disable
```
- Response: 200 OK

### /service/logs
- Get the service logs
```
curl -k -v -d '{"callback":"xyztoken", "service":"microk8s.daemon-flanneld"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/service/logs
```
- Response: 
```
-- Logs begin at Thu 2018-06-28 23:18:58 EEST, end at Tue 2020-03-24 14:30:07 EET. --
Mar 24 13:35:40 sx-tpad flanneld[27444]: warning: ignoring ServerName for user-provided CA for backwards compatibility is deprecated
Mar 24 13:35:40 sx-tpad microk8s.daemon-flanneld[27444]: I0324 13:35:40.401822   27444 main.go:244] Created subnet manager: Etcd Local Manager with Previous Subnet: 10.1.32.0/24
Mar 24 13:35:40 sx-tpad microk8s.daemon-flanneld[27444]: I0324 13:35:40.401829   27444 main.go:247] Installing signal handlers
Mar 24 13:35:40 sx-tpad microk8s.daemon-flanneld[27444]: I0324 13:35:40.409706   27444 main.go:386] Found network config - Backend type: vxlan
Mar 24 13:35:40 sx-tpad microk8s.daemon-flanneld[27444]: I0324 13:35:40.409745   27444 vxlan.go:120] VXLAN config: VNI=1 Port=0 GBP=false DirectRouting=false
Mar 24 13:35:40 sx-tpad microk8s.daemon-flanneld[27444]: I0324 13:35:40.415272   27444 local_manager.go:147] Found lease (10.1.32.0/24) for current IP (10.22.22.95), reusing
Mar 24 13:35:40 sx-tpad microk8s.daemon-flanneld[27444]: I0324 13:35:40.416885   27444 main.go:317] Wrote subnet file to /var/snap/microk8s/common/run/flannel/subnet.env
Mar 24 13:35:40 sx-tpad microk8s.daemon-flanneld[27444]: I0324 13:35:40.416910   27444 main.go:321] Running backend.
Mar 24 13:35:40 sx-tpad microk8s.daemon-flanneld[27444]: I0324 13:35:40.417111   27444 vxlan_network.go:60] watching for new subnet leases
Mar 24 13:35:40 sx-tpad microk8s.daemon-flanneld[27444]: I0324 13:35:40.418877   27444 main.go:429] Waiting for 22h59m59.99709928s to renew lease

```