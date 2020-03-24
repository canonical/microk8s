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

```
curl -k -v -d '{"callback":"xyztoken", "addon": [{"name":"dns","enable":true}]}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/configure
```
Response:
```
```

### /version

### /start
### /stop
### /status

Genera status:
```
curl -k -v -d '{"callback":"xyztoken"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/status
```
Response:
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
        * Closing connection 0 *
        TLSv1 .0(OUT),
        TLS alert,
        Client hello(1): "version": 2.6,
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
Status for an addon:
```
curl -k -v -d '{"callback":"xyztoken","addon":"dns"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/status
```
Response:
```json
{"status": "disabled", "addon": "dns"}
```
### /overview

### /addon/enable

```
curl -k -v -d '{"callback":"xyztoken","addon":"dns"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/addon/enable
```

### /addon/disable
### /services
### /service/restart
### /service/start
### /service/stop
### /service/enable
### /service/disable
### /service/logs