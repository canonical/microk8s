MAX_CHARACTERS_WRAP: int = 120
command_descriptions = {
    'add-node': "Adds a node to a cluster",
    'ambassador': "Ambassador API Gateway and Ingress",
    'cilium': "The cilium client",
    'config': "Print the kubeconfig",
    'ctr': "The containerd client",
    'dashboard-proxy': "Enable the Kubernetes dashboard and proxy to host",
    'disable': "Disables running add-ons",
    'enable': "Enables useful add-ons",
    'helm': "The helm client",
    'helm3': "The helm3 client",
    'inspect': "Checks the cluster and gathers logs",
    'istioctl': "The istio client",
    'join': "Joins this instance as a node to a cluster",
    'juju': "The Juju client",
    'kubectl': "The kubernetes client",
    'leave': "Disconnects this node from any cluster it has joined",
    'linkerd': "The linkerd client",
    'refresh-certs': "Refresh the CA certificates in this deployment",
    'remove-node': "Removes a node from the cluster",
    'reset': "Cleans the cluster from all workloads",
    'start': "Starts the kubernetes cluster",
    'status': "Displays the status of the cluster",
    'stop': "Stops the kubernetes cluster",
}
DEFAULT_CORES: int = 2
DEFAULT_MEMORY: int = 4
DEFAULT_DISK: int = 50
DEFAULT_ASSUME: bool = False
DEFAULT_CHANNEL: str = "latest/stable"
