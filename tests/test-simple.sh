#!/usr/bin/env bash

RC=0

echo "Validating MicroK8s functionality(simple)..."

echo "  Validating current node status..."
echo "    Checking service statuses..."

declare -a services=("kubelite" "containerd" "cluster-agent")

if [ -e /var/snap/microk8s/current/var/lock/clustered.lock ]
then
  services+=("apiserver-proxy")
else
  services+=("apiserver-kicker k8s-dqlite")
fi

for service in "${services[@]}"
do
    if systemctl is-active snap.microk8s.daemon-$service.service &> /dev/null; then
        echo -e "      $service \033[0;32m✔\033[0m"
    else
        echo -e "      $service \033[0;31m❌\033[0m"
        RC=1
    fi
done

if [ ! -e /var/snap/microk8s/current/var/lock/clustered.lock ]
then
    echo "  Checking node readiness..."
    microk8s kubectl get node -o json | jq -r ".items[].metadata.name" | while read -r name ; do
        STATUS=$(microk8s kubectl get node $name -o json | jq -r ".status.conditions[] | select(.type == \"Ready\") | .status")
        if [ "$STATUS" = "True" ]; then
            echo -e "    $name \033[0;32m✔\033[0m"
        else
            echo -e "    $name \033[0;31m❌\033[0m"
            RC=1
        fi
    done

    echo "  Checking Calico CNI status..."
    CNODE_DESIRED=$(microk8s kubectl get ds calico-node -o json -n kube-system | jq -r ".status.desiredNumberScheduled")
    CNODE_READY=$(microk8s kubectl get ds calico-node -o json -n kube-system | jq -r ".status.numberReady")
    if [ "$CNODE_DESIRED" = "$CNODE_READY" ]; then
        echo -e "    calico-node \033[0;32m$CNODE_READY/$CNODE_DESIRED ✔\033[0m"
    else
        echo -e "    calico-node \033[0;31m$CNODE_READY/$CNODE_DESIRED ❌\033[0m"
        RC=1
    fi

    CCONT_REPLICAS=$(microk8s kubectl get deploy calico-kube-controllers -o json -n kube-system | jq -r ".status.replicas")
    CCONT_READY=$(microk8s kubectl get deploy calico-kube-controllers -o json -n kube-system | jq -r ".status.readyReplicas")

    if [ "$CCONT_REPLICAS" = "$CCONT_READY" ]; then
        echo -e "    calico-kube-controllers \033[0;32m$CCONT_READY/$CCONT_REPLICAS ✔\033[0m"
    else
        echo -e "    calico-kube-controllers \033[0;31m$CCONT_READY/$CCONT_REPLICAS ❌\033[0m"
        RC=1
    fi

    echo "  Creating a simple deployment..."
    microk8s kubectl apply -f templates/simple-deploy.yaml &> /dev/null

    if microk8s kubectl wait --for=condition=ready pod -l app=nginx --timeout=120s &> /dev/null; then
        echo -e "    simple-deploy \033[0;32m✔\033[0m"
    else
        echo -e "    simple-deploy \033[0;31m❌\033[0m"
        RC=1
    fi

    if microk8s status --format short | grep -q "core/ingress: enabled"; then
        echo "  Checking ingress access to simple deployment..."
        if curl -s localhost:80 &> /dev/null; then
            echo -e "    ingress-reachable \033[0;32m✔\033[0m"
        else
            echo -e "    ingress-reachable \033[0;31m❌\033[0m"
            RC=1
        fi
    fi
    microk8s kubectl delete -f templates/simple-deploy.yaml --wait=true &> /dev/null
fi

exit $RC