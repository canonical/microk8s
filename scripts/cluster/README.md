# Cluster Agent REST API

## Test calls with curl

### Add the callback-token

```
sudo echo "xyztoken" > /var/snap/microk8s/current/credentials/callback-token.txt
```

### Sending the token

You can send the token-to-validate having two options:
1. Passing a json body {"callback":"\<value\>"} to the POST request and declaring a 'Content-Type' = 'application/json' header 
2. Passing the token value in a header with the name 'Callback-Token'

A curl example for getting the /version endpoint with json body or header:
```
curl -k -v -d '{"callback":"xyztoken"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/version
# or
curl -k -v -H "Callback-Token: xyztoken" -X POST https://127.0.0.1:25000/cluster/api/v1.0/version
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
- Restart flanneld
```
curl -k -v -d '{"callback":"xyztoken", "service": [{"name":"flanneld","restart":true}]}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/configure
```
- Response:
```
{"result": "ok"}
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

### /services
- Get all available services
```
curl -k -v -d '{"callback":"xyztoken"}' -H "Content-Type: application/json" -X POST https://127.0.0.1:25000/cluster/api/v1.0/services
```
- Response:
```json
{
    "services": [
        "apiserver",
        "apiserver-kicker",
        "cluster-agent",
        "containerd",
        "controller-manager",
        "etcd",
        "flanneld",
        "kubelet",
        "proxy",
        "scheduler"
    ]
}
```

### How to get Kubernetes version from k8s API
- Get version data
```
APISERVER=$(microk8s.kubectl config view --minify | grep server | cut -f 2- -d ":" | tr -d " ")
SECRET_NAME=$(microk8s.kubectl get secrets | grep ^default | cut -f1 -d ' ')
TOKEN=$(microk8s.kubectl describe secret $SECRET_NAME | grep -E '^token' | cut -f2 -d':' | tr -d " ")

curl -k $APISERVER/version --header "Authorization: Bearer $TOKEN" 

```
- Response:
```json
{
  "major": "1",
  "minor": "18",
  "gitVersion": "v1.18.2",
  "gitCommit": "52c56ce7a8272c798dbc29846288d7cd9fbae032",
  "gitTreeState": "clean",
  "buildDate": "2020-04-16T11:48:36Z",
  "goVersion": "go1.13.9",
  "compiler": "gc",
  "platform": "linux/amd64"
}
```
