#!/bin/bash

set -eux

n=0
until [ $n -ge 10 ]
do
  (sudo /snap/bin/microk8s kubectl get all --all-namespaces | grep -z "service/kubernetes") && break
  n=$[$n+1]
  if [ $n -ge 10 ]; then
    exit 1
  fi
  sleep 20
done

n=0
until [ $n -ge 3 ]
do
  (sudo /snap/bin/microk8s kubectl get no | grep -z "Ready") && exit 0
  n=$[$n+1]
  sleep 20
done

sudo /snap/bin/microk8s kubectl -n kube-system rollout status deployment.apps/calico-kube-controllers
exit 1
